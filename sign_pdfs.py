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

Cara penggunaan:
    python sign_pdfs.py
"""
"""
    signature width : 100
    paraf width : 50
"""

import importlib
import subprocess
import sys
import tempfile
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

# ################################################################ CONFIG

# Konfigurasi path
BASE_DIR = Path(__file__).parent.resolve()
ASSET_DIR = BASE_DIR / "asset"
PDF_DIR = BASE_DIR / "pdf"
OUTPUT_DIR = BASE_DIR / "pdf_output/BD"
SIGNATURE_PATH = ASSET_DIR / "paraf_bd.png"

# Konfigurasi pencarian teks dan penempatan tanda tangan
KEYWORD = "Dekan Fakultas Bisnis dan Vokasi"
SIGNED_SUFFIX = ""

# Custom Halaman | None = semua halaman.
TARGET_PAGES = None # Contoh: TARGET_PAGES = [1, 3]  -> hanya halaman 1 dan 3

# Ukuran tanda tangan (lebar dalam satuan point PDF, 1 point = 1/72 inch)
SIGNATURE_WIDTH_PT = 30  # ubah sesuai kebutuhan

# Jarak teks ke tanda tangan (dalam point)
PLACE_ABOVE_TEXT = False   # True = di atas teks, False = di bawah teks
VERTICAL_OFFSET_PT = -20

# Penempatan kanan-kiri tanda tangan relatif terhadap kotak teks keyword
HORIZONTAL_ALIGN = "left"   # "left", "center", atau "right"
HORIZONTAL_OFFSET_PT = -30   # nilai positif = ke kanan, negatif = ke kiri

# Konfigurasi flattening (rasterisasi halaman menjadi gambar)
FLATTEN_PDF = True          # True = hasil PDF akan di-flatten
FLATTEN_DPI = 500           # resolusi raster, 300 cukup untuk cetak

# ################################################################ END CONFIG

def get_signature_height(img_path: Path, target_width_pt: float) -> float:
    with Image.open(img_path) as img:
        width_px, height_px = img.size
        aspect_ratio = height_px / width_px
    return target_width_pt * aspect_ratio


def flatten_pdf(input_path: Path, output_path: Path, dpi: int = 300) -> bool:
    try:
        src_doc = fitz.open(input_path)
        dst_doc = fitz.open()

        for page in src_doc:
            # Render halaman menjadi pixmap dengan DPI tertentu
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)

            # Hitung dimensi halaman baru dalam point
            new_width_pt = pix.width * 72 / dpi
            new_height_pt = pix.height * 72 / dpi

            # Buat halaman baru dengan dimensi yang sama
            new_page = dst_doc.new_page(width=new_width_pt, height=new_height_pt)

            # Tempel gambar raster ke halaman baru
            new_page.insert_image(new_page.rect, pixmap=pix)

        dst_doc.save(output_path, deflate=True, garbage=4)
        dst_doc.close()
        src_doc.close()
        return True
    except Exception as e:
        print(f"[ERROR] Gagal flatten PDF: {e}")
        return False


def should_process_page(page_number: int) -> bool:
    if TARGET_PAGES is None:
        return True
    return page_number in TARGET_PAGES


def compute_signature_rect(text_rect, sig_height: float) -> fitz.Rect:
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
        sig_y1 = text_rect.y0 - VERTICAL_OFFSET_PT
        sig_y0 = sig_y1 - sig_height
    else:
        sig_y0 = text_rect.y1 + VERTICAL_OFFSET_PT
        sig_y1 = sig_y0 + sig_height

    return fitz.Rect(sig_x0, sig_y0, sig_x1, sig_y1)


def process_pdf(input_path: Path, output_path: Path) -> bool:
    doc = fitz.open(input_path)

    signature_count = 0
    sig_height = get_signature_height(SIGNATURE_PATH, SIGNATURE_WIDTH_PT)

    for page_number, page in enumerate(doc, start=1):
        if not should_process_page(page_number):
            continue

        # Cari semua instansi keyword di halaman ini
        text_instances = page.search_for(KEYWORD)

        for text_rect in text_instances:
            sig_rect = compute_signature_rect(text_rect, sig_height)
            page.insert_image(sig_rect, filename=str(SIGNATURE_PATH), keep_proportion=True)
            signature_count += 1

    if signature_count == 0:
        print(f"[WARN] Keyword '{KEYWORD}' tidak ditemukan di {input_path.name}. File dilewati.")
        doc.close()
        return False

    print(f"       -> Menambahkan {signature_count} tanda tangan")

    # Simpan hasil sementara (PDF yang sudah ditandatangani tapi belum flatten)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_signed_path = output_path.with_suffix(".temp_signed.pdf")
    doc.save(temp_signed_path, deflate=True, garbage=4)
    doc.close()

    # Hapus file output lama jika sudah ada agar proses penyimpanan lancar
    if output_path.exists():
        output_path.unlink()

    # Lakukan flattening jika diaktifkan
    if FLATTEN_PDF:
        flatten_ok = flatten_pdf(temp_signed_path, output_path, dpi=FLATTEN_DPI)
        if flatten_ok:
            if temp_signed_path.exists():
                temp_signed_path.unlink()  # hapus file sementara
            return True
        else:
            print("[WARN] Flattening gagal, menggunakan PDF non-flatten sebagai cadangan.")
            if output_path.exists():
                output_path.unlink()
            temp_signed_path.rename(output_path)
            return True
    else:
        if output_path.exists():
            output_path.unlink()
        temp_signed_path.rename(output_path)
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

    print(f"[INFO] Ditemukan {len(pdf_files)} file PDF untuk diproses.")
    print(f"[INFO] Flattening: {'AKTIF' if FLATTEN_PDF else 'NONAKTIF'} (DPI={FLATTEN_DPI})\n")

    success_count = 0
    skipped_count = 0

    for pdf_path in pdf_files:
        # Proses semua file PDF, termasuk yang sudah berakhiran _sign
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
