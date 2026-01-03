from pathlib import Path

from photo2pdf import ImageProcessor

if __name__ == "__main__":
    ip = ImageProcessor(
        path=Path(__file__).parent.parent / "2022",
        save_text=True,
        save_pdf=True,
        save_meta=False,
    )
    ip.process(multiprocess=False)
