import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from accounts.views import role_required

from .analisis import kelompokkan
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
            return redirect('laporan:detail', pk=laporan.pk)
    else:
        form = LaporanMingguanForm(personel=request.user)
    return render(request, 'laporan/form_laporan.html', {'form': form})


@login_required
def detail_laporan(request, pk):
    laporan = get_object_or_404(Laporan, pk=pk)
    if request.user.role != 'spv' and laporan.personel != request.user:
        raise PermissionDenied

    kelompok = kelompokkan(laporan)
    jumlah = {kategori: len(item) for kategori, item in kelompok.items()}
    return render(request, 'laporan/detail_laporan.html', {
        'laporan': laporan,
        'akhir_minggu': laporan.periode_minggu + datetime.timedelta(days=4),
        'kelompok': kelompok,
        'jumlah': jumlah,
        'total': sum(jumlah.values()),
    })