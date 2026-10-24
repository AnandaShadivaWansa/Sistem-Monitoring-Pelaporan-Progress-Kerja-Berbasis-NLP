from django.urls import path

from . import views

app_name = 'laporan'

urlpatterns = [
    path('baru/', views.buat_laporan, name='buat'),
]