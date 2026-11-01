"""
Pelatihan model klasifikasi butir kegiatan (B14).

Model : TF-IDF (unigram + bigram) + Logistic Regression (scikit-learn)
Kelas : selesai, pending, kendala, improvement
Input : CSV UTF-8 dengan kolom minimal: minggu, sumber, butir_kegiatan, label
        Baris dengan sumber berawalan S (mis. S01) dianggap data sintetis:
        hanya dipakai untuk melatih, tidak pernah dipakai untuk menguji.
Output: model.joblib  dan  laporan_evaluasi.txt

Cara pakai (dari folder proyek, venv aktif):
    python ml/train.py --data ml/data/dataset.csv
"""
import argparse
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GroupShuffleSplit, StratifiedKFold
from sklearn.pipeline import Pipeline

LABELS = ["selesai", "pending", "kendala", "improvement"]
TARGET_F1 = 0.80
MIN_ROWS_HOLDOUT = 60  # di bawah ini dipakai cross-validation, bukan split tunggal


def bersihkan(teks: str) -> str:
    """Normalisasi untuk pembanding aturan: huruf kecil, hapus simbol, rapikan spasi."""
    teks = str(teks).lower()
    teks = re.sub(r"[^a-z0-9\s]", " ", teks)
    return re.sub(r"\s+", " ", teks).strip()


def buat_pipeline() -> Pipeline:
    return Pipeline([
        # Pembersihan memakai fitur bawaan scikit-learn (huruf kecil + token alfanumerik),
        # tanpa fungsi buatan sendiri, agar model.joblib bisa dimuat dari aplikasi Django mana pun.
        ("tfidf", TfidfVectorizer(lowercase=True, token_pattern=r"(?u)\b[a-z0-9]{2,}\b",
                                  ngram_range=(1, 2), sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])


# ---------------------------------------------------------------- baseline aturan
# Pembanding sederhana (kata kunci). Urutan prioritas: kendala > pending > selesai > improvement
ATURAN = [
    ("kendala", ["kendala", "masalah", "hambatan", "gagal", "error", "terlambat", "belum bisa",
                 "belum lengkap", "tidak bisa", "rusak", "kurang"]),
    ("pending", ["menunggu", "tertunda", "ditunda", "dilanjutkan", "belum selesai", "belum dikerjakan",
                 "akan dilanjutkan", "proses", "pending"]),
    ("selesai", ["selesai", "sudah", "telah", "berhasil", "tuntas", "dikirim", "terkirim"]),
    ("improvement", ["usul", "saran", "perbaikan", "meningkatkan", "optimalkan", "mempelajari",
                     "inisiatif", "perbaiki", "efisien"]),
]


def prediksi_aturan(teks: str) -> str:
    t = bersihkan(teks)
    for label, kata in ATURAN:
        if any(k in t for k in kata):
            return label
    return "selesai"


# ---------------------------------------------------------------- utilitas
def baca_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [c.strip().lower() for c in df.columns]
    perlu = {"butir_kegiatan", "label"}
    if not perlu.issubset(df.columns):
        raise SystemExit(f"Kolom wajib tidak lengkap. Ditemukan: {list(df.columns)}")
    for kolom in ("minggu", "sumber"):
        if kolom not in df.columns:
            df[kolom] = "NA"
    df = df.dropna(subset=["butir_kegiatan", "label"]).copy()
    df["butir_kegiatan"] = df["butir_kegiatan"].astype(str).str.strip()
    df["label"] = df["label"].astype(str).str.strip().str.lower()
    df = df[df["butir_kegiatan"] != ""]
    tidak_valid = sorted(set(df["label"]) - set(LABELS))
    if tidak_valid:
        raise SystemExit(f"Label tidak dikenal: {tidak_valid}. Harus salah satu dari {LABELS}")
    return df.reset_index(drop=True)


def laporan_kelas(y_true, y_pred) -> str:
    return classification_report(y_true, y_pred, labels=LABELS, zero_division=0, digits=3)


def matriks(y_true, y_pred) -> str:
    cm = confusion_matrix(y_true, y_pred, labels=LABELS)
    kepala = "baris=aktual, kolom=prediksi\n" + " " * 14 + "".join(f"{l[:9]:>11}" for l in LABELS)
    baris = [f"{LABELS[i]:<14}" + "".join(f"{v:>11}" for v in cm[i]) for i in range(len(LABELS))]
    return "\n".join([kepala] + baris)


def split_per_kelompok(df: pd.DataFrame, seed_awal: int = 0):
    """Split 80:20 per kelompok (sumber+minggu) agar kalimat dari laporan yang sama
    tidak muncul di data latih dan data uji sekaligus (mencegah kebocoran data)."""
    kelompok = (df["sumber"].astype(str) + "_" + df["minggu"].astype(str)).values
    for seed in range(seed_awal, seed_awal + 200):
        gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)
        tr, te = next(gss.split(df, df["label"], kelompok))
        if set(df.loc[te, "label"]) == set(LABELS) and set(df.loc[tr, "label"]) == set(LABELS):
            return tr, te, seed
    return None


def sintetis_mask(df: pd.DataFrame) -> pd.Series:
    """Baris sintetis = kode sumber diawali huruf S (mis. S01). Hanya dipakai untuk melatih."""
    return df["sumber"].astype(str).str.upper().str.startswith("S")


def latih(x, y):
    return buat_pipeline().fit(x, y)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="path CSV dataset berlabel")
    ap.add_argument("--out", default="ml/model.joblib")
    ap.add_argument("--laporan", default="ml/laporan_evaluasi.txt")
    a = ap.parse_args()

    df = baca_data(Path(a.data))
    sint = sintetis_mask(df)
    asli = df[~sint].reset_index(drop=True)
    buatan = df[sint].reset_index(drop=True)
    n = len(df)

    h_asli = asli["label"].value_counts().reindex(LABELS, fill_value=0)
    h_buat = buatan["label"].value_counts().reindex(LABELS, fill_value=0)
    keluaran = [f"Jumlah baris: {n} (asli={len(asli)}, sintetis={len(buatan)})",
                "Jumlah per label (asli + sintetis):"]
    keluaran += [f"  {l}: {h_asli[l]} + {h_buat[l]}" for l in LABELS]
    kurang = [l for l in LABELS if h_asli[l] + h_buat[l] < 5]
    if kurang:
        raise SystemExit("Label dengan data < 5 baris: " + ", ".join(kurang) + ". Tambah data dulu.")
    lemah = [l for l in LABELS if h_asli[l] < 25]
    if lemah:
        keluaran.append("PERINGATAN: data ASLI < 25 baris untuk: " + ", ".join(lemah)
                        + ". Hasil evaluasi kelas ini hanya perkiraan awal.")
    if h_asli.min() < 2:
        raise SystemExit("Ada label dengan data asli < 2 baris; evaluasi tidak mungkin dilakukan.")

    # ---- evaluasi: HANYA data asli diuji; data sintetis hanya ikut melatih
    kelompok = (asli["sumber"].astype(str) + "_" + asli["minggu"].astype(str))
    split = split_per_kelompok(asli) if len(asli) >= MIN_ROWS_HOLDOUT and kelompok.nunique() >= 5 else None
    if split is not None:
        tr, te, seed = split
        x_tr = pd.concat([asli.loc[tr, "butir_kegiatan"], buatan["butir_kegiatan"]])
        y_tr = pd.concat([asli.loc[tr, "label"], buatan["label"]])
        model_eval = latih(x_tr, y_tr)
        y_true = asli.loc[te, "label"].values
        x_te = asli.loc[te, "butir_kegiatan"]
        y_pred = model_eval.predict(x_te)
        y_base = np.array([prediksi_aturan(t) for t in x_te])
        metode = (f"Metode evaluasi: hold-out per kelompok sumber+minggu, uji HANYA data asli "
                  f"(latih asli={len(tr)} + sintetis={len(buatan)}, uji asli={len(te)}, seed={seed})")
    else:
        k = int(min(5, h_asli.min()))
        skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)
        y_true_l, y_pred_l, y_base_l = [], [], []
        for tr, te in skf.split(asli["butir_kegiatan"], asli["label"]):
            x_tr = pd.concat([asli.loc[tr, "butir_kegiatan"], buatan["butir_kegiatan"]])
            y_tr = pd.concat([asli.loc[tr, "label"], buatan["label"]])
            m = latih(x_tr, y_tr)
            x_te = asli.loc[te, "butir_kegiatan"]
            y_true_l += list(asli.loc[te, "label"])
            y_pred_l += list(m.predict(x_te))
            y_base_l += [prediksi_aturan(t) for t in x_te]
        y_true, y_pred, y_base = np.array(y_true_l), np.array(y_pred_l), np.array(y_base_l)
        metode = (f"Metode evaluasi: cross-validation {k}-fold, uji HANYA data asli "
                  f"(data sintetis={len(buatan)} hanya ikut melatih; hasil bersifat perkiraan awal)")

    dukungan = pd.Series(y_true).value_counts().reindex(LABELS, fill_value=0)
    f1_model = f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0)
    f1_base = f1_score(y_true, y_base, labels=LABELS, average="macro", zero_division=0)
    keluaran += [
        "", metode,
        "Jumlah data uji per label: " + ", ".join(f"{l}={dukungan[l]}" for l in LABELS), "",
        "== MODEL (TF-IDF + Logistic Regression) ==", laporan_kelas(y_true, y_pred),
        "Confusion matrix:", matriks(y_true, y_pred), "",
        "== PEMBANDING (aturan kata kunci) ==", laporan_kelas(y_true, y_base), "",
        f"F1 macro model     : {f1_model:.3f}",
        f"F1 macro pembanding: {f1_base:.3f}",
        f"Selisih            : {f1_model - f1_base:+.3f}",
        f"Target F1 >= {TARGET_F1:.2f}: " + ("TERCAPAI" if f1_model >= TARGET_F1 else "belum tercapai"),
    ]

    # ---- latih model final dengan seluruh data (asli + sintetis) lalu simpan
    final = latih(df["butir_kegiatan"], df["label"])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": final, "labels": LABELS, "jumlah_data": n,
                 "f1_macro_evaluasi": float(f1_model)}, a.out)
    keluaran += ["", f"Model disimpan ke: {a.out}"]

    teks = "\n".join(keluaran)
    print(teks)
    Path(a.laporan).parent.mkdir(parents=True, exist_ok=True)
    Path(a.laporan).write_text(teks, encoding="utf-8")


if __name__ == "__main__":
    main()