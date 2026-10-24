from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.login_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('laporan/', views.halaman_personel, name='halaman_personel'),
    path('dashboard/', views.dashboard_spv, name='dashboard_spv'),
]
