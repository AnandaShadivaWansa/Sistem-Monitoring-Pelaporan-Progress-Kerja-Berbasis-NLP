from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('personel', 'Personel'),
        ('spv', 'SPV'),
    ]
    TIM_CHOICES = [
        ('scrap', 'Scrap Personnel'),
        ('inspection', 'Inspection Personnel'),
        ('hse', 'HSE'),
        ('cctv', 'CCTV Team'),
        ('facility_5s', 'Facility & 5S'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='personel')
    tim = models.CharField(max_length=20, choices=TIM_CHOICES, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"