"""Ringkasan mingguan otomatis dengan algoritma TextRank (B17).

Cara kerja TextRank:
1. Setiap kalimat diubah menjadi vektor angka dengan TF-IDF.
2. Kemiripan antar kalimat dihitung dengan cosine similarity.
3. Kalimat dianggap simpul pada graf; kalimat yang mirip dengan banyak
   kalimat lain mendapat skor tinggi (dihitung seperti PageRank).
4. Beberapa kalimat dengan skor tertinggi dipilih sebagai ringkasan,
   lalu ditampilkan sesuai urutan aslinya agar tetap runtut.
"""
import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

REDAMAN = 0.85        # damping factor PageRank
ITERASI_MAKS = 100
TOLERANSI = 1e-6
MAKS_PROGRESS = 3     # jumlah kalimat ringkasan bagian Progress
MAKS_KENDALA = 2      # jumlah kalimat ringkasan bagian Kendala
MIN_KATA = 3          # kalimat yang terlalu pendek diabaikan


TANPA_ISI = {'', '-', '--', 'tidak ada', 'nihil', 'n/a'}


def rapikan(teks):
    """Menggabungkan baris menjadi satu kalimat dan membuang titik/spasi di ujung."""
    teks = re.sub(r'\s+', ' ', teks or '').strip(' -•\t')
    return teks.rstrip('.').strip()


def skor_textrank(kalimat):
    """Menghitung skor TextRank untuk setiap kalimat."""
    n = len(kalimat)
    if n == 0:
        return np.array([])
    if n == 1:
        return np.array([1.0])
    try:
        vektor = TfidfVectorizer(lowercase=True,
                                 token_pattern=r'(?u)\b[a-z0-9]{2,}\b').fit_transform(kalimat)
    except ValueError:
        # semua kalimat tidak memiliki kata yang bisa dihitung
        return np.ones(n) / n

    kemiripan = cosine_similarity(vektor)
    np.fill_diagonal(kemiripan, 0)

    # normalisasi per baris: bobot "suara" tiap kalimat ke kalimat lain
    total_baris = kemiripan.sum(axis=1, keepdims=True)
    transisi = np.divide(kemiripan, total_baris,
                         out=np.full_like(kemiripan, 1 / n), where=total_baris > 0)

    skor = np.ones(n) / n
    for _ in range(ITERASI_MAKS):
        baru = (1 - REDAMAN) / n + REDAMAN * transisi.T.dot(skor)
        if np.abs(baru - skor).sum() < TOLERANSI:
            skor = baru
            break
        skor = baru
    return skor


def pilih_kalimat(kalimat, maks):
    """Mengambil `maks` kalimat dengan skor tertinggi, urut sesuai posisi asli."""
    kalimat = list(dict.fromkeys(kalimat))  # buang kalimat yang sama persis
    if len(kalimat) <= maks:
        return kalimat
    skor = skor_textrank(kalimat)
    terpilih = sorted(np.argsort(-skor)[:maks])
    return [kalimat[i] for i in terpilih]


def buat_ringkasan(kelompok):
    """Membuat teks ringkasan dari hasil `kelompokkan(laporan)`.

    kelompok: dict {kategori: [KegiatanHarian, ...]}
    Bagian Progress diambil dari kegiatan selesai, pending, dan improvement;
    bagian Kendala diambil dari kegiatan berkategori kendala.
    """
    def kumpulkan(kategori_list):
        # Satu kegiatan harian = satu kalimat ringkasan:
        # "kegiatan: hasil" (Progress) atau "kegiatan: masalah" (Kendala).
        kalimat = []
        for kategori in kategori_list:
            for kegiatan in kelompok.get(kategori, []):
                detail = kegiatan.masalah if kategori == 'kendala' else kegiatan.hasil
                teks = rapikan(kegiatan.kegiatan)
                detail = rapikan(detail)
                if detail and detail.lower() not in TANPA_ISI:
                    if len(detail) > 1 and detail[1].islower():
                        detail = detail[0].lower() + detail[1:]  # "Selesai" -> "selesai", "HSE" tetap
                    teks = f'{teks}: {detail}'
                if len(teks.split()) >= MIN_KATA:
                    kalimat.append(teks + '.')
        return kalimat

    progress = pilih_kalimat(kumpulkan(['selesai', 'pending', 'improvement']), MAKS_PROGRESS)
    kendala = pilih_kalimat(kumpulkan(['kendala']), MAKS_KENDALA)

    baris = ['Progress:']
    baris += [f'- {k}' for k in progress] or ['- Tidak ada progres tercatat.']
    baris += ['', 'Kendala:']
    baris += [f'- {k}' for k in kendala] or ['- Tidak ada kendala.']
    return '\n'.join(baris)