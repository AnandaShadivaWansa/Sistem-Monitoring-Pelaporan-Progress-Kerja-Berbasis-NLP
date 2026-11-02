import logging
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

KATEGORI_URUT = ['selesai', 'pending', 'kendala', 'improvement']

TANPA_ISI = {'', '-', '--', 'tidak ada', 'nihil', 'n/a'}

KATA_IMPROVEMENT = (
    'improvement', 'peningkatan', 'optimasi', 'optimalisasi',
    'usulan', 'saran', 'perbaikan proses',
)

BELUM_SELESAI = ('belum selesai', 'tidak selesai')

# Model NLP hasil pelatihan (dibuat oleh ml/train.py).
MODEL_PATH = Path(settings.BASE_DIR) / 'ml' / 'model.joblib'

# Jika keyakinan model di bawah angka ini, kegiatan dikategorikan dengan aturan.
AMBANG_KEYAKINAN = 0.35

_cache = {'mtime': None, 'model': None, 'versi': 'aturan'}


def _kosong(teks):
    return teks.strip().lower().rstrip('.') in TANPA_ISI


def klasifikasi_aturan(kegiatan):
    """Menentukan kategori satu kegiatan harian berdasarkan aturan."""
    if not _kosong(kegiatan.masalah):
        return 'kendala'

    hasil = kegiatan.hasil.lower()
    if 'selesai' in hasil and not any(k in hasil for k in BELUM_SELESAI):
        return 'selesai'

    teks = f'{kegiatan.kegiatan} {kegiatan.tindakan}'.lower()
    if any(k in teks for k in KATA_IMPROVEMENT):
        return 'improvement'

    return 'pending'


def _muat_model():
    """Memuat model terlatih. Dimuat ulang otomatis bila file model berubah.
    Mengembalikan None jika model tidak tersedia (aplikasi tetap jalan dengan aturan)."""
    try:
        mtime = MODEL_PATH.stat().st_mtime
    except OSError:
        _cache.update(mtime=None, model=None, versi='aturan')
        return None

    if _cache['mtime'] != mtime:
        try:
            import joblib
            data = joblib.load(MODEL_PATH)
            _cache['model'] = data['model']
            _cache['versi'] = f"tfidf-logreg-{data.get('jumlah_data', '?')}baris"
        except Exception:
            logger.exception('Model NLP gagal dimuat, memakai aturan.')
            _cache.update(model=None, versi='aturan')
        _cache['mtime'] = mtime
    return _cache['model']


def _teks_untuk_model(kegiatan):
    """Menggabungkan isian satu hari menjadi satu teks untuk model."""
    bagian = [kegiatan.kegiatan, kegiatan.masalah, kegiatan.tindakan, kegiatan.hasil]
    return '. '.join(b.strip() for b in bagian if not _kosong(b))


def klasifikasi_banyak(daftar_kegiatan):
    """Mengklasifikasikan banyak kegiatan sekaligus.
    Mengembalikan daftar (kategori, skor, sumber); sumber = 'model' atau 'aturan'."""
    daftar = list(daftar_kegiatan)
    hasil = [None] * len(daftar)
    model = _muat_model()

    if model is not None:
        teks = [_teks_untuk_model(k) for k in daftar]
        indeks = [i for i, t in enumerate(teks) if t]
        if indeks:
            try:
                proba = model.predict_proba([teks[i] for i in indeks])
                kelas = [str(c) for c in model.classes_]
                for baris, i in zip(proba, indeks):
                    j = int(baris.argmax())
                    skor = float(baris[j])
                    if kelas[j] in KATEGORI_URUT and skor >= AMBANG_KEYAKINAN:
                        hasil[i] = (kelas[j], round(skor, 2), 'model')
            except Exception:
                logger.exception('Prediksi model gagal, memakai aturan.')

    for i, kegiatan in enumerate(daftar):
        if hasil[i] is None:
            hasil[i] = (klasifikasi_aturan(kegiatan), None, 'aturan')
    return hasil


def klasifikasi(kegiatan):
    """Kategori satu kegiatan harian: model NLP bila tersedia, jika tidak aturan."""
    return klasifikasi_banyak([kegiatan])[0][0]


def analisis_laporan(laporan):
    """Mengklasifikasikan semua kegiatan sebuah laporan lalu menyimpan hasilnya
    (HasilAnalisis + ItemKlasifikasi) dan memperbarui status_analisis.
    Tidak pernah melempar error: bila gagal, status menjadi 'gagal'."""
    from django.db import transaction

    from .models import HasilAnalisis, ItemKlasifikasi, Laporan

    Laporan.objects.filter(pk=laporan.pk).update(status_analisis='proses')
    try:
        daftar = list(laporan.kegiatan.all())
        hasil_klasifikasi = klasifikasi_banyak(daftar)
        versi = _cache['versi'] if any(s == 'model' for _, _, s in hasil_klasifikasi) else 'aturan'

        with transaction.atomic():
            hasil, _ = HasilAnalisis.objects.update_or_create(
                laporan=laporan, defaults={'versi_model': versi},
            )
            for kegiatan, (kategori, skor, _sumber) in zip(daftar, hasil_klasifikasi):
                # kategori_koreksi (koreksi SPV) sengaja tidak diubah oleh analisis ulang.
                ItemKlasifikasi.objects.update_or_create(
                    kegiatan=kegiatan,
                    defaults={
                        'hasil': hasil,
                        'isi_item': _teks_untuk_model(kegiatan) or kegiatan.kegiatan,
                        'kategori_model': kategori,
                        'skor_keyakinan': skor,
                    },
                )
        status = 'selesai'
    except Exception:
        logger.exception('Analisis laporan %s gagal.', laporan.pk)
        status = 'gagal'

    Laporan.objects.filter(pk=laporan.pk).update(status_analisis=status)
    laporan.status_analisis = status
    if status == 'selesai':
        perbarui_ringkasan(laporan)
    return status


def perbarui_ringkasan(laporan):
    """Membuat ringkasan TextRank dari kegiatan yang sudah dikelompokkan
    (koreksi SPV ikut diperhitungkan) lalu menyimpannya ke HasilAnalisis.ringkasan.
    Kegagalan ringkasan tidak memengaruhi hasil klasifikasi."""
    from .models import HasilAnalisis
    from .ringkasan import buat_ringkasan

    try:
        teks = buat_ringkasan(kelompokkan(laporan))
        HasilAnalisis.objects.filter(laporan=laporan).update(ringkasan=teks)
        return teks
    except Exception:
        logger.exception('Ringkasan laporan %s gagal dibuat.', laporan.pk)
        return ''


def kelompokkan(laporan):
    """Mengelompokkan kegiatan satu laporan per kategori.
    Memakai hasil yang tersimpan (koreksi SPV diutamakan); jika belum ada,
    kategori dihitung langsung."""
    hasil = {kategori: [] for kategori in KATEGORI_URUT}
    daftar = list(laporan.kegiatan.select_related('klasifikasi'))

    belum = []
    for kegiatan in daftar:
        item = getattr(kegiatan, 'klasifikasi', None)
        if item is None:
            belum.append(kegiatan)
            continue
        kategori = item.kategori_koreksi or item.kategori_model
        kegiatan.kategori_ml = kategori
        kegiatan.skor_ml = item.skor_keyakinan
        kegiatan.sumber_ml = 'koreksi' if item.kategori_koreksi else 'tersimpan'
        hasil[kategori].append(kegiatan)

    for kegiatan, (kategori, skor, sumber) in zip(belum, klasifikasi_banyak(belum)):
        kegiatan.kategori_ml = kategori
        kegiatan.skor_ml = skor
        kegiatan.sumber_ml = sumber
        hasil[kategori].append(kegiatan)

    for kategori in hasil:
        hasil[kategori].sort(key=lambda k: k.tanggal)
    return hasil