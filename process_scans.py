import signal
import sys
import time
from multiprocessing import Pool
from pathlib import Path
from types import FrameType

from tqdm import tqdm

from subsys.date_extraction import extract_date
from subsys.image_ocr import ImageOCR
from subsys.image_ocr import tesseract_language_query
from subsys.image_ocr import tesseract_languages
from subsys.keyword_extraction import extract_keywords
from subsys.logger import log

path_scans = Path(__file__).parent / "2022"
language_ids = tesseract_language_query(["de", "en"])
save_text = True
save_pdf = True
save_meta = False


def exit_gracefully(_signum: int, _frame: FrameType | None) -> None:
    pool.terminate()
    log.warning("Exiting!")
    sys.exit(0)


def process_file(path: Path) -> None:
    path_pdf = path.with_suffix(".pdf")
    path_text = path.with_suffix(".txt")
    path_meta = path.with_suffix(".yaml")

    need_pdf = save_pdf and not path_pdf.exists()
    need_text = save_text and not path_text.exists()
    need_meta = save_meta and not path_meta.exists()

    if not (need_pdf or need_text or need_meta):
        return

    log.debug(f"processing {path.name}")
    ocr = ImageOCR(path)
    lang_id = ocr.detect_lang_id()
    content = ocr.get_content()

    if need_pdf:
        ocr.save_pdf(path_pdf)

    if content is None:
        log.debug("\t-> OCR found no text in image, will skip saving content & metadata")
        return

    if need_text:
        ocr.save_content(path_text)

    if not need_meta:
        return

    # get metadata, TODO: safe in yaml
    keywords = extract_keywords(content, lang_id)
    if keywords is not None and len(keywords) > 0:
        log.debug(f"\t-> found keywords: {keywords}")
    date_str = extract_date(content, lang_id)
    if date_str is not None:
        log.debug(f"\t-> extracting date: {date_str}")
    osd = ocr.get_osd()
    if osd:
        log.debug(f"\t-> osd: {osd}")
    # TODO: optimize detection by rotation, BW, inversion?


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, exit_gracefully)
    signal.signal(signal.SIGINT, exit_gracefully)
    # increase_verbose_level(3)
    log.info(f"tesseract langs: {tesseract_languages()}")

    file_items: list[Path] = [
        x
        for x in path_scans.iterdir()
        if x.is_file() and x.suffix.lower() in [".jpg", ".jpeg", ".bmp", ".png", ".tif"]
    ]
    timestamp_start = time.time()

    # for file in file_items:
    #    process_file(file)

    with Pool() as pool:
        log.info(f"Multiproccesing with {pool._processes} workers")

        def exit_pool(_signum: int, _frame: FrameType | None) -> None:
            pool.terminate()
            log.warning("Exiting!")
            sys.exit(0)

        signal.signal(signal.SIGTERM, exit_pool)
        signal.signal(signal.SIGINT, exit_pool)

        progress_bar = tqdm(
            total=len(file_items),
            desc="  .. processing files",
            unit="n",
            leave=False,
        )

        # pool.map(process_file, file_items)
        for _ in pool.imap(process_file, file_items):
            progress_bar.update(n=1)

    log.debug(f"\t-> processing took {round(time.time() - timestamp_start, 2)} s")
    # TODO: join multi-pdf
