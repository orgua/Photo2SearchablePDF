import os
import time
from datetime import date
from pathlib import Path
from typing import List

import pytesseract as pta
from dateparser.search import search_dates
from langid.langid import LanguageIdentifier, model

from framework_ocr import ocr_pdf, ocr_osd, ocr_text
from opencv_filtering import SheetFilter
from pdf_compressor import CompressPDF
from rake_nltk import Rake  # TODO: nltk needs a post-setup: python -c "import nltk; nltk.download('stopwords')"

# Config
pta.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
ghostscript_path = r"C:\Program Files\gs\gs9.53.3\bin\gswin64c.exe"  # +c is the console version

file_path_jpg_raw = "./2020_B_Jpg/"
file_path_jpg_crop = "./2020_C_filtered/"
file_path_pdf_pta = "./2020_D_pdf/"
file_path_pdf_cmp = "./2020_E_pdfc/"
file_path_named = "./2020_F_named/"
# TODO: these folder have to be created manually, currently

languages = ["deu", "eng"]  # tesseract-format, mixing is possible
paper_format_mm = (210, 297)

# dateparser should only take full
dateparser_settings = {'STRICT_PARSING': True,
                       'REQUIRE_PARTS': ['day', 'month', 'year'],
                       'PREFER_LOCALE_DATE_ORDER': True,
                       'PARSERS': ['custom-formats', 'absolute-time'],  # custom-formats, timestamp
                       }

custom_keyword_path = "keywords_custom.txt"

date_year_limits = [2010, date.today().year]  # lower and upper threshold

for language in languages:
    if not language in pta.get_languages():
        raise ValueError(f"Language '{languages}' is currently not supported, choose one of {pta.get_languages()}")
languages_pta = "+".join(languages)

langid2nltk_lang_dict = {"de": "german", "en": "english"}
# TODO: output of one lib does not fit into others
#   for nltk see https://pypi.org/project/stop-words/
#   tesseract is even stranger


def import_list(input_file: str) -> List[str]:
    with open(input_file, "r", encoding="utf-8-sig") as logfile:
        data = logfile.readlines()

        data = [date[0:date.find("#")] for date in data]  # filter from # anywhere to end of line
        #data = [date.lower() for date in data]

        data = [date.replace("   ", " ") for date in data]  # 3 spaces
        data = [date.replace("  ", " ") for date in data]  # 2 spaces

        data = [date.replace(" ", " ") for date in data]  # a special space, looks the same..
        data = [date.replace("	", " ") for date in data]  # TAB

        data = [date.replace("\n", "") for date in data]
        data = [date.replace("\r", "") for date in data]
        data = [date.replace(",", " ") for date in data]
        data = [date.strip() for date in data]  # remove whitespace from beginning and end
        data = [date for date in data if len(date) > 0]
        return data


def str_filter(input: str) -> str:
    input = input.lower()
    # newlines
    input = input.replace("\n", "").replace("\r", "")
    # punctuation
    input = input.replace(".", " ").replace("!", " ").replace("?", " ").replace(",", " ")
    # special characters
    input = input.replace("	", " ")  # TAB
    input = input.replace(" ", " ")  # a special space, looks the same..
    input = input.replace("   ", " ")  # 3 spaces
    input = input.replace("  ", " ")  # 2 spaces
    return input


if __name__ == '__main__':

    sheet = SheetFilter(paper_format_mm, 1)

    file_items = [x for x in os.scandir(file_path_jpg_raw) if x.is_file()]

    sheet.open_picture(file_items[0].path)
    #sheet.demo_enhance_details()

    pdfc = CompressPDF(2, ghostscript_path, show_info=False)
    lang_id = LanguageIdentifier.from_modelstring(model, norm_probs=True)

    if Path(custom_keyword_path).exists():
        custom_keywords = import_list(custom_keyword_path)
    else:
        custom_keywords = list([])

    for file in file_items:
        # use the fast-lane if image exists
        file_name_pdf = ".".join(file.name.split(".")[:-1]) + ".pdf"
        if Path(file_path_pdf_cmp + file_name_pdf).exists():
            print(f"skipping {file.name} because resulting pdf already exists")
            continue

        print(f"processing {file.name}")
        timestamp_start = time.time()

        sheet.open_picture(file.path)
        response = sheet.correct_perspective()
        if not response:
            print(f"   -> had trouble correcting the image, will skip this one")
            continue

        sheet.crop()
        sheet.enhance_details(darken_percent=50)  # TODO: should be named: turn B/W
        sheet.save(file_path_jpg_crop + file.name)
        doc_size = sheet.get_size_mm()

        response = ocr_pdf(sheet.export_for_tesseract(), file_path_pdf_pta + file_name_pdf, languages_pta)
        if not response:
            print(f"   -> OCR found no text in image, will skip pdf-generation")
            continue

        pdfc.compress(file_path_pdf_pta + file_name_pdf, file_path_pdf_cmp + file_name_pdf, doc_size)

        # extract meta-data
        file_name_txt = ".".join(file.name.split(".")[:-1]) + ".txt"
        text_osd = ocr_osd(file_path_jpg_crop + file.name, languages_pta)
        text_ocr = ocr_text(file_path_jpg_crop + file.name, languages_pta)
        text_filtered = str_filter(text_ocr)

        try:
            text_lang = lang_id.classify(text_ocr)  # TODO for later: rerun ocr with proper language
        except KeyError:
            text_lang = ("en", 0.0)

        if text_lang[0] not in langid2nltk_lang_dict:
            print(f"  -> WARNING: had an unknown language: {text_lang}")
            text_lang = ("en", 0.0)


        rake = Rake(language=langid2nltk_lang_dict[text_lang[0]], min_length=1, max_length=4)
        rake.extract_keywords_from_text(text_ocr)
        text_keywords = rake.get_ranked_phrases()
        text_dates = search_dates(text_ocr, settings=dateparser_settings, languages=[text_lang[0]], add_detected_language=True)

        # limit dates and sort from newest to oldest
        if text_dates:
            text_datetimes = [x[1] for x in text_dates]
            # TODO: further limit / filter dates for plausibility - e.g. span of last 5 +- 5 years
            # TODO: trouble with switched month / day on timestamps with day < 13, e.g. 02.12.2020
            text_datetimes = [x for x in text_datetimes if x.year >= 1971]
            text_datetimes = [x for x in text_datetimes if x.year <= date_year_limits[1]]
            text_datetimes = sorted(text_datetimes, key=lambda p: p.timestamp(), reverse=True)
            if text_datetimes:
                date_stamp = text_datetimes[0].strftime("%Y-%m-%d")
            else:
                date_stamp = "none"
        else:
            date_stamp = "none"

        text_custom_keywords = list([])
        for keyword in custom_keywords:
            if text_filtered.find(keyword.lower()) >= 0:
                text_custom_keywords.append(keyword)

        print(f" -> date={date_stamp}, lang={text_lang[0]}, keywords={text_custom_keywords}")

        text_content = "### Metadata ###\n" +\
                       f"file: {file_name_pdf}\n" +\
                       f"date: {text_dates}\n" +\
                       f"language: {text_lang}\n" +\
                       f"keywords: {text_keywords}\n" +\
                       f"custom keywords: {text_custom_keywords}\n" + "\n\n\n\n" +\
                       "### STATISTICS / OSD ###\n" +\
                       text_osd + "\n\n\n\n" + \
                       "### TEXT ###\n" +\
                       text_ocr

        if text_custom_keywords:
            file_name_txt = date_stamp + " " + " - ".join(text_custom_keywords) + ".txt"
            file_name_pdfc = date_stamp + " " + " - ".join(text_custom_keywords) + ".pdf"
        else:
            file_name_txt = date_stamp + " " + file_name_txt
            file_name_pdfc = date_stamp + " " + file_name_pdf

        pdfc.compress(file_path_pdf_pta + file_name_pdf, file_path_named + file_name_pdfc, doc_size)

        # TODO: check if file exists
        with open(file_path_named + file_name_txt, 'wb') as f:
            f.write(text_content.encode("utf-8-sig"))

        print(f" -> took {round(time.time() - timestamp_start,2)} s")
