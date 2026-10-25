KATEGORI_URUT = ['selesai', 'pending', 'kendala', 'improvement']

TANPA_ISI = {'', '-', '--', 'tidak ada', 'nihil', 'n/a'}

KATA_IMPROVEMENT = (
    'improvement', 'peningkatan', 'optimasi', 'optimalisasi',
    'usulan', 'saran', 'perbaikan proses',
)

BELUM_SELESAI = ('belum selesai', 'tidak selesai')


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


def kelompokkan(laporan):
    """Mengelompokkan kegiatan satu laporan per kategori."""
    hasil = {kategori: [] for kategori in KATEGORI_URUT}
    for kegiatan in laporan.kegiatan.all():
        hasil[klasifikasi_aturan(kegiatan)].append(kegiatan)
    return hasil