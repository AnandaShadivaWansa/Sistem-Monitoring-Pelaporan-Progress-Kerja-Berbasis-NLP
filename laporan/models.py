from django.conf import settings
from django.db import models


class Laporan(models.Model):
    STATUS_ANALISIS = [
        ('belum', 'Belum dianalisis'),
        ('proses', 'Sedang dianalisis'),
        ('selesai', 'Selesai dianalisis'),
        ('gagal', 'Gagal dianalisis'),
    ]

    personel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='laporan',
    )
    periode_minggu = models.DateField(help_text='Tanggal Senin dari minggu laporan')
    status_analisis = models.CharField(
        max_length=10, choices=STATUS_ANALISIS, default='belum'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-periode_minggu']
        constraints = [
            models.UniqueConstraint(
                fields=['personel', 'periode_minggu'],
                name='unik_laporan_per_personel_per_minggu',
            )
        ]

    def __str__(self):
        return f'{self.personel} - {self.periode_minggu}'


class KegiatanHarian(models.Model):
    laporan = models.ForeignKey(
        Laporan, on_delete=models.CASCADE, related_name='kegiatan'
    )
    tanggal = models.DateField()
    kegiatan = models.TextField()
    masalah = models.TextField(blank=True)
    tindakan = models.TextField(blank=True)
    hasil = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['tanggal']
        constraints = [
            models.UniqueConstraint(
                fields=['laporan', 'tanggal'],
                name='unik_kegiatan_per_hari',
            )
        ]

    def __str__(self):
        return f'{self.laporan} - {self.tanggal}'


class Lampiran(models.Model):
    STATUS_EKSTRAKSI = [
        ('belum', 'Belum diekstrak'),
        ('berhasil', 'Berhasil'),
        ('gagal', 'Gagal'),
    ]

    laporan = models.ForeignKey(
        Laporan, on_delete=models.CASCADE, related_name='lampiran'
    )
    file = models.FileField(upload_to='lampiran/')
    nama_file_asli = models.CharField(max_length=255)
    tipe_file = models.CharField(max_length=50)
    ukuran_byte = models.PositiveIntegerField()
    status_ekstraksi = models.CharField(
        max_length=10, choices=STATUS_EKSTRAKSI, default='belum'
    )
    teks_ekstraksi = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nama_file_asli


class HasilAnalisis(models.Model):
    laporan = models.OneToOneField(
        Laporan, on_delete=models.CASCADE, related_name='hasil_analisis'
    )
    versi_model = models.CharField(max_length=50, blank=True)
    ringkasan = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Hasil {self.laporan}'


class ItemKlasifikasi(models.Model):
    KATEGORI = [
        ('selesai', 'Selesai'),
        ('pending', 'Pending'),
        ('kendala', 'Kendala'),
        ('improvement', 'Improvement'),
    ]

    hasil = models.ForeignKey(
        HasilAnalisis, on_delete=models.CASCADE, related_name='item'
    )
    kegiatan = models.OneToOneField(
        KegiatanHarian,
        on_delete=models.CASCADE,
        related_name='klasifikasi',
        null=True,
        blank=True,
    )
    isi_item = models.TextField()
    kategori_model = models.CharField(max_length=12, choices=KATEGORI)
    skor_keyakinan = models.FloatField(null=True, blank=True)
    kategori_koreksi = models.CharField(
        max_length=12, choices=KATEGORI, blank=True
    )

    def __str__(self):
        return f'{self.kategori_model}: {self.isi_item[:40]}'


class Feedback(models.Model):
    laporan = models.ForeignKey(
        Laporan, on_delete=models.CASCADE, related_name='feedback'
    )
    penulis = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='feedback_ditulis',
    )
    isi = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Feedback {self.laporan}'