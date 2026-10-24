from django.contrib import admin

from .models import (
    Feedback,
    HasilAnalisis,
    ItemKlasifikasi,
    KegiatanHarian,
    Lampiran,
    Laporan,
)

admin.site.register(Laporan)
admin.site.register(KegiatanHarian)
admin.site.register(Lampiran)
admin.site.register(HasilAnalisis)
admin.site.register(ItemKlasifikasi)
admin.site.register(Feedback)