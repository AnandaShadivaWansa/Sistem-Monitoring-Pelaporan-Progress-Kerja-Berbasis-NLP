from django.urls import path

from . import views

app_name = 'laporan'

urlpatterns = [
    path('baru/', views.buat_laporan, name='buat'),
    path('<int:pk>/', views.detail_laporan, name='detail'),
    path('<int:pk>/feedback/', views.tambah_feedback, name='feedback'),
]