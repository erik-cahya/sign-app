import fitz
from pathlib import Path

PDF_DIR = Path("pdf")

keyword = "Dekan Fakultas Informatika dan Komputer"

pdf_files = sorted(PDF_DIR.glob("*.pdf"))
if not pdf_files:
    print("Tidak ada file PDF di folder pdf/")
    exit(1)

for pdf_path in pdf_files[:3]:  # periksa 3 file pertama
    print(f"\n=== {pdf_path.name} ===")
    doc = fitz.open(pdf_path)
    for page_num, page in enumerate(doc, start=1):
        text_instances = page.search_for(keyword)
        if text_instances:
            print(f"  Halaman {page_num}: ditemukan {len(text_instances)} instance")
            for i, rect in enumerate(text_instances):
                print(f"    [{i}] x0={rect.x0:.2f}, y0={rect.y0:.2f}, x1={rect.x1:.2f}, y1={rect.y1:.2f}")
            # tampilkan dimensi halaman
            print(f"    Dimensi halaman: {page.rect.width:.2f} x {page.rect.height:.2f}")
    doc.close()
