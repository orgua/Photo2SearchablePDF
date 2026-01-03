from pathlib import Path

from subsys.image_ocr import tesseract_language_query
from subsys.main_processing import ImageProcessor
from subsys.main_processing import ImageProcessorConfig

language_ids = tesseract_language_query(["de", "en"])

if __name__ == "__main__":
    cfg = ImageProcessorConfig(
        path=Path(__file__).parent / "2022",
        save_text=True,
        save_pdf=True,
        save_meta=False,
    )
    ip = ImageProcessor(cfg)
    ip.process(multiprocess=True)
