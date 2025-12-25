import time
from pathlib import Path

import pytesseract as pta
from rake_nltk import Rake

from subsys.image_ocr import ocr_osd
from subsys.image_ocr import ocr_pdf
from subsys.image_ocr import ocr_text
from subsys.language_detection import detect_lang
from subsys.logger import log
from subsys.pdf_compressor import CompressPDF
from subsys.photo_preprocessing import SheetFilter
from subsys.string_cleaning import import_list
from subsys.string_cleaning import str_filter

# Config
pta.pytesseract.tesseract_cmd = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe").as_posix()
ghostscript_path = Path(r"C:\Program Files\gs\gs9.53.3\bin\gswin64c.exe")
# +c is the console version

path_here = Path(__file__).parent
file_path_jpg_raw = path_here / "2020_B_Jpg"
file_path_jpg_crop = path_here / "2020_C_filtered/"
file_path_pdf_pta = path_here / "2020_D_pdf/"
file_path_pdf_cmp = path_here / "2020_E_pdfc/"
file_path_named = path_here / "2020_F_named/"
# TODO: these folder have to be created manually, currently

languages = ["deu", "eng"]  # tesseract-format, mixing is possible
paper_format_mm = (210, 297)


custom_keyword_path = path_here / "keywords_custom.txt"


for language in languages:
    if language not in pta.get_languages():
        raise ValueError(
            f"Language '{languages}' is currently not supported, choose one of {pta.get_languages()}"
        )
languages_pta = "+".join(languages)


if __name__ == "__main__":
    sheet = SheetFilter(paper_format_mm, 1)

    file_items: list[Path] = [x for x in file_path_jpg_raw.iterdir() if x.is_file()]

    sheet.open_picture(file_items[0])
    # sheet.demo_enhance_details()

    pdfc = CompressPDF(2, ghostscript_path, show_info=False)
    lang_id = LanguageIdentifier.from_modelstring(model, norm_probs=True)

    if custom_keyword_path.exists():
        custom_keywords = import_list(custom_keyword_path)
    else:
        custom_keywords = []

    for file in file_items:
        # use the fast-lane if image exists
        file_name_pdf = file.with_suffix(".pdf").name
        if (file_path_pdf_cmp / file_name_pdf).exists():
            log.debug(f"skipping {file.name} because resulting pdf already exists")
            continue

        log.info(f"processing {file.name}")
        timestamp_start = time.time()

        sheet.open_picture(file)
        response = sheet.correct_perspective()
        if not response:
            log.debug("\t-> had trouble correcting the image, will skip this one")
            continue

        sheet.crop()
        sheet.enhance_details(darken_percent=50)  # TODO: should be named: turn B/W
        sheet.save(file_path_jpg_crop / file.name)
        doc_size = sheet.get_size_mm()

        response = ocr_pdf(
            sheet.export_for_tesseract(), file_path_pdf_pta / file_name_pdf, languages_pta
        )
        if not response:
            log.debug("\t-> OCR found no text in image, will skip pdf-generation")
            continue

        pdfc.compress(
            file_path_pdf_pta / file_name_pdf, file_path_pdf_cmp / file_name_pdf, doc_size
        )

        # extract meta-data
        file_name_txt = file.with_suffix(".txt").name
        text_osd = ocr_osd(file_path_jpg_crop / file.name, languages_pta)
        text_ocr = ocr_text(file_path_jpg_crop / file.name, languages_pta)
        text_filtered = str_filter(text_ocr)

        lang_id = detect_lang(text_ocr)

        rake = Rake(language=langid2nltk_lang_dict[text_lang[0]], min_length=1, max_length=4)
        rake.extract_keywords_from_text(text_ocr)
        text_keywords = rake.get_ranked_phrases()

        date_stamp = extract_date(text_ocr, lang_id)

        text_custom_keywords = []
        for keyword in custom_keywords:
            if text_filtered.find(keyword.lower()) >= 0:
                text_custom_keywords.append(keyword)

        log.debug(f" -> date={date_stamp}, lang={text_lang[0]}, keywords={text_custom_keywords}")

        text_content = (
            "### Metadata ###\n"
            f"file: {file_name_pdf}\n"
            f"date: {text_dates}\n"
            f"language: {text_lang}\n"
            f"keywords: {text_keywords}\n"
            f"custom keywords: {text_custom_keywords}\n"
            "\n\n\n\n"
            "### STATISTICS / OSD ###\n" + text_osd + "\n\n\n\n" + "### TEXT ###\n" + text_ocr
        )

        if text_custom_keywords:
            file_name_txt = date_stamp + " " + " - ".join(text_custom_keywords) + ".txt"
            file_name_pdfc = date_stamp + " " + " - ".join(text_custom_keywords) + ".pdf"
        else:
            file_name_txt = date_stamp + " " + file_name_txt
            file_name_pdfc = date_stamp + " " + file_name_pdf

        pdfc.compress(file_path_pdf_pta / file_name_pdf, file_path_named / file_name_pdfc, doc_size)

        # TODO: check if file exists
        with (file_path_named / file_name_txt).open("wb") as f:
            f.write(text_content.encode("utf-8-sig"))

        log.debug(f"\t-> took {round(time.time() - timestamp_start, 2)} s")
