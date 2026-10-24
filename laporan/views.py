from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render

from accounts.views import role_required

from .forms import LaporanMingguanForm
from .models import KegiatanHarian, Laporan


@role_required('personel')
def buat_laporan(request):
    if request.method == 'POST':
        form = LaporanMingguanForm(request.POST, personel=request.user)
        if form.is_valid():
            with transaction.atomic():
                laporan = Laporan.objects.create(
                    personel=request.user,
                    periode_minggu=form.cleaned_data['periode_minggu'],
                )
                KegiatanHarian.objects.bulk_create([
                    KegiatanHarian(laporan=laporan, **data)
                    for data in form.data_kegiatan()
                ])
            messages.success(request, 'Laporan berhasil disimpan.')
            return redirect('accounts:halaman_personel')
    else:
        form = LaporanMingguanForm(personel=request.user)
    return render(request, 'laporan/form_laporan.html', {'form': form})