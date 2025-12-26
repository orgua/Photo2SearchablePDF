import signal
import sys
import time
from pathlib import Path
from types import FrameType

from subsys.date_extraction import extract_date
from subsys.image_ocr import ocr_osd
from subsys.image_ocr import ocr_pdf
from subsys.image_ocr import ocr_text
from subsys.image_ocr import tesseract_language_query
from subsys.keyword_extraction import extract_keywords
from subsys.language_detection import detect_lang
from subsys.logger import increase_verbose_level
from subsys.logger import log

path_scans = Path(r"C:\scans2023")
language_ids = tesseract_language_query(["de", "en"])


def exit_gracefully(_signum: int, _frame: FrameType | None) -> None:
    log.warning("Exiting!")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, exit_gracefully)
    signal.signal(signal.SIGINT, exit_gracefully)
    increase_verbose_level(3)

    file_items: list[Path] = [
        x
        for x in path_scans.iterdir()
        if x.is_file() and x.suffix.lower() in [".jpg", ".jpeg", ".bmp", ".png", ".tif"]
    ]

    # TODO: can be multiprocessed
    # TODO: put in subfn like get_content, get_metadata, create_pdf

    for file in file_items:
        # use the fast-lane if image exists
        log.info(f"processing {file.name}")
        timestamp_start = time.time()

        path_txt = file.with_suffix(".txt")
        if path_txt.exists():
            log.debug(
                "\tskipping txt-extraction because resulting file already exists -> will load content"
            )
            with path_txt.open(encoding="utf-8-sig") as txt:
                contents = txt.readlines()
                content = "\n".join(contents)
        else:
            content = ocr_text(file, language_ids)
            if content is not None:
                lang_ids = detect_lang(content)
                if lang_ids is not None:
                    content = ocr_text(file, language_ids) or content
                with path_txt.open("w", encoding="utf-8-sig") as txt:
                    txt.write(content)

        # get metadata, TODO: safe in yaml
        if content:
            lang_ids = detect_lang(content)
            lang_ids = [lang_ids] if lang_ids is not None else language_ids
            keywords = extract_keywords(content, lang_ids[0])
            if keywords is not None and len(keywords) > 0:
                log.debug(f"\t-> found keywords: {keywords}")
            date_str = extract_date(content, lang_ids[0])
            if date_str is not None:
                log.debug(f"\t-> extracting date: {date_str}")
            osd = ocr_osd(file, lang_ids)
            if osd:
                log.debug(f"\t-> osd: {osd}")
        else:
            lang_ids = language_ids
        # TODO: optimize detection by rotation, BW, inversion?

        path_pdf = file.with_suffix(".pdf")
        if path_pdf.exists():
            log.debug("\tskipping pdf-creation because resulting file already exists")
        else:
            response = ocr_pdf(file, path_pdf, lang_ids)
            if not response:
                log.debug("\t-> OCR found no text in image, will skip pdf-generation")

        # TODO: join multi-pdf
