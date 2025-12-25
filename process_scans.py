import time
from datetime import date
from pathlib import Path

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


paper_format_mm = (210, 297)

# dateparser should only take full
dateparser_settings = {
    "STRICT_PARSING": True,
    "REQUIRE_PARTS": ["day", "month", "year"],
    "PREFER_LOCALE_DATE_ORDER": True,
    "PARSERS": ["custom-formats", "absolute-time"],  # custom-formats, timestamp
}

path_here = Path(__file__).parent
custom_keyword_path = path_here / "keywords_custom.txt"

date_year_limits = [2010, date.today().year]  # lower and upper threshold


langid2nltk_lang_dict = {"de": "german", "en": "english"}
# TODO: output of one lib does not fit into others
#   for nltk see https://pypi.org/project/stop-words/
#   tesseract is even stranger


if __name__ == "__main__":
    increase_verbose_level(3)

    file_items: list[Path] = [
        x
        for x in path_scans.iterdir()
        if x.is_file() and x.suffix.lower() in [".jpg", ".jpeg", ".bmp", ".png", ".tif"]
    ]

    # TODO: can be multiprocessed

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
            if content:
                with path_txt.open("w", encoding="utf-8-sig") as txt:
                    txt.write(content)
        if content is None:
            log.debug("\t-> OCR found no text in image, will skip txt-generation")
            continue  # TODO: just create pdf

        # get metadata
        lang_ids = detect_lang(content)
        lang_ids = [lang_ids] if lang_ids is not None else language_ids
        keywords = extract_keywords(content, lang_ids[0])
        if keywords is not None and len(keywords) > 0:
            log.debug(f"\t-> found keywords: {keywords}")
        date_str = extract_date(content, lang_ids[0])
        if date_str is not None:
            log.debug(f"\t-> extracting date: {date_str}")
        osd = ocr_osd(file, lang_ids)
        log.debug(f"\t-> osd: {osd}")
        # TODO: optimize detection by rotation, BW, inversion?

        path_pdf = file.with_suffix(".pdf")
        if path_pdf.exists():
            log.debug("\tskipping pdf-creation because resulting file already exists")
        else:
            response = ocr_pdf(file, path_pdf, lang_ids)
            if not response:
                log.debug("\t-> OCR found no text in image, will skip pdf-generation")

        # TODO: join multi-pdf

        continue
