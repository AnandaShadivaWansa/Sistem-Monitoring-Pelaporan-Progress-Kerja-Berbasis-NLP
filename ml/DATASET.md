# Kartu Dataset – Klasifikasi Butir Kegiatan WorkPulse

Dataset berisi kalimat butir kegiatan dari laporan kerja mingguan, masing-masing diberi satu label status. Dataset dipakai untuk melatih model TF-IDF + Logistic Regression yang mengelompokkan kegiatan secara otomatis.

**Versi:** v3 · **Diperbarui:** 28 November 2026 · **Jumlah:** 295 baris

## 1. Sumber Data

| Kode sumber | Jenis | Keterangan |
|---|---|---|
| L01 | Magang | Logbook kegiatan harian selama magang |
| K01 | Kantor | Laporan kerja mingguan di lingkungan kantor |
| S01 | Sintetis | Kalimat buatan untuk menambah contoh label Improvement; hanya dipakai untuk melatih, tidak pernah untuk menguji |

## 2. Struktur Kolom

| Kolom | Isi | Contoh |
|---|---|---|
| `minggu` | Kode minggu laporan | M12 |
| `sumber` | Kode sumber data (lihat bagian 1) | K01 |
| `orang` | Kode pelapor, bukan nama asli | K01 |
| `butir_kegiatan` | Satu kalimat kegiatan | Perbaikan pompa air tertunda menunggu kapasitor |
| `label` | Status kegiatan (lihat bagian 3) | kendala |

## 3. Definisi Label

| Label | Dipakai bila | Kata yang sering muncul |
|---|---|---|
| `selesai` | Pekerjaan sudah tuntas | selesai, sudah, berhasil, normal kembali |
| `pending` | Belum tuntas tetapi tanpa masalah: sedang berjalan atau menunggu | menunggu, dalam proses, dilanjutkan, dijadwalkan |
| `kendala` | Ada hambatan yang membuat pekerjaan tertahan | rusak, gagal, error, terhambat, tidak bisa |
| `improvement` | Usulan atau perbaikan cara kerja, bukan tugas rutin | usulan, perbaikan proses, digitalisasi, efisiensi |

Jika satu kalimat memenuhi lebih dari satu label, prioritasnya: **kendala > pending > selesai > improvement**.

## 4. Jumlah Data

| Jenis | Selesai | Pending | Kendala | Improvement | Total |
|---|---|---|---|---|---|
| Kantor | 69 | 65 | 16 | 8 | 158 |
| Magang | 64 | 33 | 16 | 3 | 116 |
| Sintetis | 0 | 0 | 0 | 21 | 21 |
| **Total** | **133** | **98** | **32** | **32** | **295** |

## 5. Pembagian Data Latih dan Data Uji

- Data uji diambil **20% dari data asli** (magang dan kantor). Data sintetis tidak pernah masuk data uji.
- Pembagian dilakukan **per kelompok laporan (sumber + minggu)**, sehingga kalimat dari laporan yang sama tidak muncul di data latih dan data uji sekaligus.
- Pembagian memastikan keempat label ada di data latih maupun data uji.

| File | Jumlah | Selesai | Pending | Kendala | Improvement |
|---|---|---|---|---|---|
| `latih.csv` | 247 | 110 | 85 | 22 | 30 |
| `uji.csv` | 48 | 23 | 13 | 10 | 2 |

## 6. Proses Pembersihan

1. Menghapus spasi berlebih dan baris kosong.
2. Menyeragamkan label menjadi huruf kecil dan membuang label di luar empat kategori.
3. Membuang kalimat ganda (tanpa membedakan huruf besar dan kecil).
4. Mencatat kalimat yang sama tetapi berlabel berbeda ke `cek_label.csv` untuk diperiksa manual.

## 7. Hasil Evaluasi (versi ini)

| Ukuran | Nilai |
|---|---|
| F1 macro model | 0,840 |
| F1 macro pembanding (aturan kata kunci) | 0,503 |
| F1 macro data uji kantor (31 baris) | 0,979 |
| F1 macro data uji magang (17 baris) | 0,503 |

## 8. Privasi

- Nama pelapor diganti kode. Daftar pasangan nama dan kode disimpan terpisah dan tidak dibagikan.
- File data (`ml/data/`) tidak diunggah ke repository; repository hanya berisi kode dan dokumentasi ini.

## 9. Batasan

- Label **Improvement** dari data asli baru 11 baris; sisanya data sintetis.
- Label **Kendala** baru 32 baris, dan model masih sering salah membedakan Kendala dengan Pending.
- Data uji magang belum memuat label Improvement, sehingga nilai per jenis data masih perkiraan awal.

## 10. Cara Membuat Ulang

```
python ml/siapkan_dataset.py --data ml/data/dataset.csv
python ml/train.py --data ml/data/latih.csv --uji ml/data/uji.csv
```