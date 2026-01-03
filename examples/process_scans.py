from pathlib import Path

from photo2pdf.image_ocr import tesseract_language_query
from photo2pdf.main_processing import ImageProcessor

language_ids = tesseract_language_query(["de", "en"])

if __name__ == "__main__":
    ip = ImageProcessor(
        path=Path(__file__).parent / "2022",
        save_text=True,
        save_pdf=True,
        save_meta=False,
    )
    ip.process(multiprocess=True)
