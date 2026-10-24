import datetime

from django import forms

from .models import Laporan

HARI = [
    ('senin', 'Senin'),
    ('selasa', 'Selasa'),
    ('rabu', 'Rabu'),
    ('kamis', 'Kamis'),
    ('jumat', 'Jumat'),
]


class LaporanMingguanForm(forms.Form):
    periode_minggu = forms.DateField(
        label='Minggu (pilih tanggal Senin)',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    def __init__(self, *args, personel=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.personel = personel
        for key, _ in HARI:
            self.fields[f'{key}_kegiatan'] = forms.CharField(
                label='Kegiatan', required=False,
                widget=forms.Textarea(attrs={'rows': 2}),
            )
            self.fields[f'{key}_masalah'] = forms.CharField(
                label='Masalah', required=False,
                widget=forms.Textarea(attrs={'rows': 2}),
            )
            self.fields[f'{key}_tindakan'] = forms.CharField(
                label='Tindakan', required=False,
                widget=forms.Textarea(attrs={'rows': 2}),
            )
            self.fields[f'{key}_hasil'] = forms.CharField(
                label='Hasil', required=False,
                widget=forms.Textarea(attrs={'rows': 2}),
            )

    def clean_periode_minggu(self):
        tanggal = self.cleaned_data['periode_minggu']
        if tanggal.weekday() != 0:
            raise forms.ValidationError('Tanggal harus hari Senin.')
        if Laporan.objects.filter(
            personel=self.personel, periode_minggu=tanggal
        ).exists():
            raise forms.ValidationError(
                'Laporan untuk minggu ini sudah ada.'
            )
        return tanggal

    def clean(self):
        data = super().clean()
        ada_isi = False
        for key, nama in HARI:
            kegiatan = data.get(f'{key}_kegiatan', '').strip()
            lainnya = any(
                data.get(f'{key}_{f}', '').strip()
                for f in ('masalah', 'tindakan', 'hasil')
            )
            if kegiatan:
                ada_isi = True
            elif lainnya:
                self.add_error(
                    f'{key}_kegiatan',
                    f'Isi kegiatan hari {nama} terlebih dahulu.',
                )
        if not ada_isi and not self.errors:
            raise forms.ValidationError(
                'Isi minimal satu hari kegiatan.'
            )
        return data

    def blok_hari(self):
        return [
            {
                'nama': nama,
                'kegiatan': self[f'{key}_kegiatan'],
                'masalah': self[f'{key}_masalah'],
                'tindakan': self[f'{key}_tindakan'],
                'hasil': self[f'{key}_hasil'],
            }
            for key, nama in HARI
        ]

    def data_kegiatan(self):
        hasil = []
        senin = self.cleaned_data['periode_minggu']
        for i, (key, _) in enumerate(HARI):
            kegiatan = self.cleaned_data.get(f'{key}_kegiatan', '').strip()
            if not kegiatan:
                continue
            hasil.append({
                'tanggal': senin + datetime.timedelta(days=i),
                'kegiatan': kegiatan,
                'masalah': self.cleaned_data.get(f'{key}_masalah', '').strip(),
                'tindakan': self.cleaned_data.get(f'{key}_tindakan', '').strip(),
                'hasil': self.cleaned_data.get(f'{key}_hasil', '').strip(),
            })
        return hasil