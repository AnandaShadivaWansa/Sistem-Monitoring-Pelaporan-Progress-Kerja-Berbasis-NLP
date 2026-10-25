import datetime

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect

from laporan.analisis import kelompokkan
from laporan.models import Laporan


def redirect_by_role(user):
    if user.role == 'spv':
        return redirect('accounts:dashboard_spv')
    return redirect('accounts:halaman_personel')


def role_required(role):
    def decorator(view):
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.role != role:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


def login_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)
    error = None
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password'),
        )
        if user is not None:
            login(request, user)
            return redirect_by_role(user)
        error = 'Username atau password salah.'
    return render(request, 'accounts/login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@role_required('personel')
def halaman_personel(request):
    daftar_laporan = request.user.laporan.all()
    return render(
        request,
        'accounts/personel.html',
        {'daftar_laporan': daftar_laporan},
    )


@role_required('spv')
def dashboard_spv(request):
    tim = request.GET.get('tim', '')
    minggu = request.GET.get('minggu', '')

    semua = Laporan.objects.select_related('personel').prefetch_related('kegiatan')
    if tim:
        semua = semua.filter(personel__tim=tim)
    if minggu:
        try:
            semua = semua.filter(
                periode_minggu=datetime.date.fromisoformat(minggu)
            )
        except ValueError:
            minggu = ''

    daftar = []
    daftar_kendala = []
    for laporan in semua:
        kelompok = kelompokkan(laporan)
        jumlah = {kategori: len(item) for kategori, item in kelompok.items()}
        daftar.append({'laporan': laporan, 'jumlah': jumlah})
        for kegiatan in kelompok['kendala']:
            daftar_kendala.append({'laporan': laporan, 'kegiatan': kegiatan})

    ringkasan = {
        'total_laporan': len(daftar),
        'laporan_berkendala': sum(1 for d in daftar if d['jumlah']['kendala'] > 0),
        'total_kendala': sum(d['jumlah']['kendala'] for d in daftar),
        'total_selesai': sum(d['jumlah']['selesai'] for d in daftar),
    }

    pilihan_tim = sorted(
        {t for t in Laporan.objects.values_list('personel__tim', flat=True) if t}
    )
    pilihan_minggu = (
        Laporan.objects.order_by('-periode_minggu')
        .values_list('periode_minggu', flat=True)
        .distinct()
    )

    return render(request, 'accounts/spv.html', {
        'daftar': daftar,
        'daftar_kendala': daftar_kendala[:5],
        'ringkasan': ringkasan,
        'tim': tim,
        'minggu': minggu,
        'pilihan_tim': pilihan_tim,
        'pilihan_minggu': pilihan_minggu,
    })