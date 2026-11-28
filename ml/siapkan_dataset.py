"""
Penyiapan dataset klasifikasi butir kegiatan.

Langkah:
  1. Menggabungkan satu atau lebih file CSV berlabel (mis. dataset.csv + data kantor baru).
  2. Membersihkan data: rapikan spasi, label huruf kecil, buang baris kosong dan kalimat ganda.
  3. Memisahkan data per jenis sumber ke file berbeda:
        magang.csv   -> sumber berawalan L atau bertuliskan "magang"
        kantor.csv   -> sumber berawalan K atau bertuliskan "kantor"
        sintetis.csv -> sumber berawalan S atau bertuliskan "sintetis"
  4. Membuat data latih dan data uji di file terpisah:
        uji.csv   -> 20% data ASLI (magang + kantor), dibagi per kelompok sumber+minggu
                     agar kalimat dari laporan yang sama tidak bocor ke data latih
        latih.csv -> sisa data asli + seluruh data sintetis
  5. Mencatat kalimat yang sama tetapi berlabel berbeda ke cek_label.csv untuk diperiksa manual.

Cara pakai (dari folder proyek, venv aktif):
    python ml/siapkan_dataset.py --data ml/data/dataset.csv ml/data/kantor_baru.csv
"""
import argparse
from pathlib import Path

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

LABELS = ["selesai", "pending", "kendala", "improvement"]
KOLOM = ["minggu", "sumber", "orang", "butir_kegiatan", "label"]


def jenis_sumber(sumber: str) -> str:
    s = str(sumber).strip().lower()
    if s.startswith("s") or s == "sintetis":
        return "sintetis"
    if s.startswith("l") or s == "magang":
        return "magang"
    if s.startswith("k") or s == "kantor":
        return "kantor"
    return "lainnya"


def baca(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [c.strip().lower() for c in df.columns]
    if not {"butir_kegiatan", "label", "sumber"}.issubset(df.columns):
        raise SystemExit(f"{path}: kolom wajib butir_kegiatan, label, sumber. Ditemukan: {list(df.columns)}")
    for kolom in KOLOM:
        if kolom not in df.columns:
            df[kolom] = "NA"
    df["asal_file"] = path.name
    return df[KOLOM + ["asal_file"]]


def bersihkan(df: pd.DataFrame) -> pd.DataFrame:
    awal = len(df)
    df = df.dropna(subset=["butir_kegiatan", "label"]).copy()
    for kolom in KOLOM:
        df[kolom] = df[kolom].astype(str).str.strip()
    df["butir_kegiatan"] = df["butir_kegiatan"].str.replace(r"\s+", " ", regex=True)
    df["label"] = df["label"].str.lower()
    df = df[df["butir_kegiatan"] != ""]
    salah = df[~df["label"].isin(LABELS)]
    if not salah.empty:
        print(f"\n[!] {len(salah)} baris berlabel tidak dikenal (dibuang):")
        print(salah[["asal_file", "butir_kegiatan", "label"]].head(20).to_string(index=False))
        df = df[df["label"].isin(LABELS)]
    df["jenis"] = df["sumber"].map(jenis_sumber)
    lain = df[df["jenis"] == "lainnya"]
    if not lain.empty:
        print(f"\n[!] {len(lain)} baris dengan kode sumber tidak dikenal (dibuang): "
              f"{sorted(lain['sumber'].unique())[:10]}")
        df = df[df["jenis"] != "lainnya"]
    print(f"\nPembersihan: {awal} baris -> {len(df)} baris")
    return df.reset_index(drop=True)


def cek_konflik(df: pd.DataFrame, folder: Path) -> pd.DataFrame:
    """Kalimat sama (setelah huruf kecil) tetapi labelnya berbeda -> perlu dicek manual."""
    kunci = df["butir_kegiatan"].str.lower()
    jumlah_label = df.groupby(kunci)["label"].nunique()
    konflik_kunci = set(jumlah_label[jumlah_label > 1].index)
    konflik = df[kunci.isin(konflik_kunci)].sort_values("butir_kegiatan")
    path = folder / "cek_label.csv"
    if not konflik.empty:
        konflik.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"\n[!] {len(konflik_kunci)} kalimat punya label berbeda. Daftar lengkap: {path}")
    elif path.exists():
        path.unlink()
    return konflik


def buang_ganda(df: pd.DataFrame) -> pd.DataFrame:
    kunci = df["butir_kegiatan"].str.lower()
    sebelum = len(df)
    df = df[~kunci.duplicated(keep="first")].reset_index(drop=True)
    if sebelum != len(df):
        print(f"Kalimat ganda dibuang: {sebelum - len(df)} baris")
    return df


def bagi_latih_uji(asli: pd.DataFrame, porsi_uji: float):
    kelompok = (asli["sumber"] + "_" + asli["minggu"]).values
    for seed in range(300):
        gss = GroupShuffleSplit(n_splits=1, test_size=porsi_uji, random_state=seed)
        tr, te = next(gss.split(asli, asli["label"], kelompok))
        if set(asli.loc[te, "label"]) == set(LABELS) and set(asli.loc[tr, "label"]) == set(LABELS):
            return tr, te, seed
    raise SystemExit("Tidak menemukan pembagian yang memuat semua label di latih dan uji. Tambah data.")


def ringkasan(judul: str, df: pd.DataFrame):
    tabel = (df.groupby(["jenis", "label"]).size().unstack(fill_value=0)
             .reindex(columns=LABELS, fill_value=0))
    tabel["total"] = tabel.sum(axis=1)
    print(f"\n== {judul}: {len(df)} baris ==")
    print(tabel.to_string())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", nargs="+", required=True, help="satu atau lebih file CSV berlabel")
    ap.add_argument("--folder", default="ml/data", help="folder hasil")
    ap.add_argument("--uji", type=float, default=0.2, help="porsi data uji dari data asli (default 0.2)")
    a = ap.parse_args()

    folder = Path(a.folder)
    folder.mkdir(parents=True, exist_ok=True)

    df = pd.concat([baca(Path(p)) for p in a.data], ignore_index=True)
    df = bersihkan(df)
    cek_konflik(df, folder)
    df = buang_ganda(df)
    ringkasan("Data bersih", df)

    # ---- pisah per jenis sumber
    for jenis in ("magang", "kantor", "sintetis"):
        bagian = df[df["jenis"] == jenis]
        bagian[KOLOM].to_csv(folder / f"{jenis}.csv", index=False, encoding="utf-8-sig")
        print(f"Disimpan: {folder / (jenis + '.csv')} ({len(bagian)} baris)")

    # ---- pisah latih dan uji (uji hanya dari data asli)
    asli = df[df["jenis"] != "sintetis"].reset_index(drop=True)
    sint = df[df["jenis"] == "sintetis"]
    tr, te, seed = bagi_latih_uji(asli, a.uji)
    latih = pd.concat([asli.loc[tr], sint], ignore_index=True)
    uji = asli.loc[te].reset_index(drop=True)
    latih[KOLOM].to_csv(folder / "latih.csv", index=False, encoding="utf-8-sig")
    uji[KOLOM].to_csv(folder / "uji.csv", index=False, encoding="utf-8-sig")
    ringkasan(f"Data latih (seed={seed})", latih)
    ringkasan("Data uji (hanya data asli)", uji)
    print(f"\nDisimpan: {folder / 'latih.csv'} dan {folder / 'uji.csv'}")


if __name__ == "__main__":
    main()