"""
Script untuk menambahkan tanda tangan otomatis ke PDF transkrip nilai.

Struktur folder:
    pdfSignature/
    ├── asset/
    │   └── sign.png          -> gambar tanda tangan (dengan alpha/transparan)
    ├── pdf/
    │   └── *.pdf             -> PDF yang akan ditandatangani
    ├── pdf_output/
    │   └── *_signed.pdf       -> hasil PDF yang sudah ditandatangani
    └── sign_pdfs.py          -> script ini

Menjalankan Program:
    python sign_pdfs.py
"""

import importlib
import subprocess
import sys
from pathlib import Path


def ensure_dependencies():
    required = [("PyMuPDF", "fitz"), ("Pillow", "PIL")]
    missing = []

    for package_name, import_name in required:
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append(package_name)

    if missing:
        print(f"[INFO] Dependency belum terinstall: {', '.join(missing)}")
        print("[INFO] Menginstall dependency, harap tunggu...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install"] + missing,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Gagal menginstall dependency: {e}")
            print("[ERROR] Coba install manual dengan: python -m pip install PyMuPDF Pillow")
            sys.exit(1)
        print("[INFO] Dependency berhasil diinstall.\n")

    # Re-import untuk memastikan modul sudah tersedia di namespace global
    for _, import_name in required:
        try:
            importlib.import_module(import_name)
        except ImportError as e:
            print(f"[ERROR] Gagal mengimport modul '{import_name}' setelah install: {e}")
            sys.exit(1)


# Pastikan dependency tersedia sebelum import modul pihak ketiga
ensure_dependencies()

import fitz  # PyMuPDF
from PIL import Image

# Konfigurasi path
BASE_DIR = Path(__file__).parent.resolve()
ASSET_DIR = BASE_DIR / "asset"
PDF_DIR = BASE_DIR / "pdf"
OUTPUT_DIR = BASE_DIR / "pdf_output"
SIGNATURE_PATH = ASSET_DIR / "sign.png"

# Konfigurasi pencarian teks dan penempatan tanda tangan
KEYWORD = "Dekan Fakultas Informatika dan Komputer"
SIGNED_SUFFIX = "_signed"

# Ukuran tanda tangan (lebar dalam satuan point PDF, 1 point = 1/72 inch)
SIGNATURE_WIDTH_PT = 120  # ubah sesuai kebutuhan

# Jarak teks ke tanda tangan (dalam point)
PLACE_ABOVE_TEXT = False   # True = di atas teks, False = di bawah teks
VERTICAL_OFFSET_PT = 8

# Penempatan kanan-kiri tanda tangan relatif terhadap kotak teks keyword
HORIZONTAL_ALIGN = "left"   # "left", "center", atau "right"
HORIZONTAL_OFFSET_PT = 30        # nilai positif = ke kanan, negatif = ke kiri


def get_signature_height(img_path: Path, target_width_pt: float) -> float:
    """
    Menghitung tinggi gambar tanda tangan (dalam point PDF)
    berdasarkan lebar yang diinginkan, mempertahankan rasio aspek.
    """
    with Image.open(img_path) as img:
        width_px, height_px = img.size
        aspect_ratio = height_px / width_px
    return target_width_pt * aspect_ratio


def process_pdf(input_path: Path, output_path: Path) -> bool:
    """
    Membuka PDF, mencari keyword, lalu menempelkan tanda tangan di posisi
    yang diatur oleh konfigurasi (atas/bawah teks, kiri/tengah/kanan secara
    horizontal, beserta offset masing-masing).
    Mengembalikan True jika berhasil, False jika gagal.
    """
    doc = fitz.open(input_path)

    signature_inserted = False

    for page in doc:
        # Cari semua instansi keyword di halaman ini
        text_instances = page.search_for(KEYWORD)

        if not text_instances:
            continue

        # Ambil kotak teks pertama yang cocok
        text_rect = text_instances[0]

        # Hitung lebar dan tinggi tanda tangan
        sig_height = get_signature_height(SIGNATURE_PATH, SIGNATURE_WIDTH_PT)

        # Posisikan tanda tangan secara horizontal berdasarkan alignment
        align = HORIZONTAL_ALIGN.lower()
        if align == "left":
            sig_x0 = text_rect.x0 + HORIZONTAL_OFFSET_PT
        elif align == "right":
            sig_x0 = text_rect.x1 - SIGNATURE_WIDTH_PT + HORIZONTAL_OFFSET_PT
        else:  # default: center
            center_x = (text_rect.x0 + text_rect.x1) / 2
            sig_x0 = center_x - (SIGNATURE_WIDTH_PT / 2) + HORIZONTAL_OFFSET_PT
        sig_x1 = sig_x0 + SIGNATURE_WIDTH_PT

        # Posisikan tanda tangan: di atas atau di bawah teks
        if PLACE_ABOVE_TEXT:
            # Letakkan tanda tangan di atas teks keyword
            sig_y1 = text_rect.y0 - VERTICAL_OFFSET_PT
            sig_y0 = sig_y1 - sig_height
        else:
            # Letakkan tanda tangan di bawah teks keyword
            sig_y0 = text_rect.y1 + VERTICAL_OFFSET_PT
            sig_y1 = sig_y0 + sig_height

        sig_rect = fitz.Rect(sig_x0, sig_y0, sig_x1, sig_y1)

        # Sisipkan gambar tanda tangan ke halaman
        page.insert_image(sig_rect, filename=str(SIGNATURE_PATH), keep_proportion=True)

        signature_inserted = True
        break  # hanya proses keyword pertama yang ditemukan

    if not signature_inserted:
        print(f"[WARN] Keyword '{KEYWORD}' tidak ditemukan di {input_path.name}. File dilewati.")
        doc.close()
        return False

    # Simpan hasil PDF
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path, deflate=True, garbage=4)
    doc.close()
    return True


def main():
    if not SIGNATURE_PATH.exists():
        print(f"[ERROR] Gambar tanda tangan tidak ditemukan: {SIGNATURE_PATH}")
        return

    if not PDF_DIR.exists():
        print(f"[ERROR] Folder PDF tidak ditemukan: {PDF_DIR}")
        return

    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        print("[WARN] Tidak ada file PDF di folder pdf/")
        return

    print(f"[INFO] Ditemukan {len(pdf_files)} file PDF untuk diproses.\n")

    success_count = 0
    skipped_count = 0

    for pdf_path in pdf_files:
        # Hindari memproses file yang sudah berakhiran _signed (jika ada di input)
        if pdf_path.stem.endswith(SIGNED_SUFFIX):
            print(f"[SKIP] Melewati file yang sudah ditandatangani: {pdf_path.name}")
            skipped_count += 1
            continue

        output_filename = f"{pdf_path.stem}{SIGNED_SUFFIX}.pdf"
        output_path = OUTPUT_DIR / output_filename

        print(f"[PROC] Memproses: {pdf_path.name} -> {output_filename}")

        if process_pdf(pdf_path, output_path):
            success_count += 1
        else:
            skipped_count += 1

    print(f"\n[DONE] Selesai. Berhasil: {success_count}, Dilewati: {skipped_count}")
    print(f"[OUT] Hasil disimpan di: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
