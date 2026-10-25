from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect


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
    return render(request, 'accounts/spv.html')
