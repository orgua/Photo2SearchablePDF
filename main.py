import os
import time

from opencv_filtering import SheetFilter
from pdf_compressor import CompressPDF

try:
    from PIL import Image
except ImportError:
    import Image

import pytesseract as pta

# Config
pta.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
ghostscript_path = r"C:\Program Files\gs\gs9.53.3\bin\gswin64.exe"

file_path_jpg_raw = "./2020_B_Jpg/"
file_path_jpg_crop = "./2020_C_filtered/"
file_path_pdf_pta = "./2020_D_pdf/"
file_path_pdf_cmp = "./2020_E_pdfc/"

file_path = "2021_DocTest/2021-02-05_20-05-19__DSC3928.jpg"
language = "deu"
paper_format_mm = (210, 297)  # TODO: use as dpi-source for gs

if not language in pta.get_languages():
    raise ValueError(f"Language '{language}' is currently not supported, choose one of {pta.get_languages()}")

#os.symlink(path_gs, './gs')
#os.link(path_gs, './gs')
#subprocess.call(['cmd', '/c', 'mklink', 'gs', path_gs], shell=True)
#subprocess.call(['mklink', 'gs', path_gs], shell=True)
# admin-shell: mklink gs.exe "C:\Program Files\gs\gs9.53.3\bin\gswin64.exe"

# TODO:
# - add lib for compressing pdfs
#   - old: https://github.com/pts/pdfsizeopt
#   - small sideproject: https://github.com/theeko74/pdfc
#       - https://itheo.nl/repair-and-compress-pdf-files-with-python/
#   - pyPDF2 - dead for 4 years https://stackoverflow.com/questions/22776388/pypdf2-compression
#       - alternatives: https://stackoverflow.com/questions/63199763/maintained-alternatives-to-pypdf2
#   - commercial pdfTron https://www.pdftron.com/documentation/samples/py/OptimizerTest
# - improve picture before OCR
#   - https://github.com/unpaper/unpaper
#   - pre-recognition lib, https://github.com/leha-bot/PRLib


def ocr_pdf_from_file(file_path: str):
    # Get a searchable PDF
    pdf = pta.image_to_pdf_or_hocr(file_path, extension='pdf', lang=language)
    filename = ".".join(file_path.split(".")[:-1]) + ".pdf"
    with open(filename, 'w+b') as f:
        f.write(pdf)


def ocr_pdf(image_data, file_path_output: str):
    # Get a searchable PDF
    pdf = pta.image_to_pdf_or_hocr(image_data, extension='pdf', lang=language)
    with open(file_path_output, 'w+b') as f:
        f.write(pdf)


def ocr_core(filename):  # TODO: use image data directly
    # This function will handle the core OCR processing of images.
    text = pta.image_to_osd(Image.open(filename), lang=language)
    text += "\n\n\n\n"
    text += pta.image_to_string(Image.open(filename), lang=language)
    return text


if __name__ == '__main__':

    sheet = SheetFilter(paper_format_mm, 1)

    file_items = [x for x in os.scandir(file_path_jpg_raw) if x.is_file()]

    sheet.open_picture(file_items[0].path)
    #sheet.demo_enhance_details()

    pdfc = CompressPDF(2, ghostscript_path, show_info=False)

    for file in file_items:
        print(f"processing {file.name}")
        timestamp_start = time.time()

        sheet.open_picture(file.path)
        response = sheet.correct_perspective()
        if not response:
            print(f"   -> had trouble correcting the image, will skip this one")
            continue

        sheet.crop()
        sheet.enhance_details(55)
        sheet.save(file_path_jpg_crop + file.name)
        #dpi = sheet.get_dpi()

        file_name_pdf = ".".join(file.name.split(".")[:-1]) + ".pdf"

        ocr_pdf(sheet.export_for_tesseract(), file_path_pdf_pta + file_name_pdf)

        filenameA = ".".join(file_path.split(".")[:-1]) + ".pdf"

        pdfc.compress(file_path_pdf_pta + file_name_pdf, file_path_pdf_cmp + file_name_pdf)

        file_name_txt = ".".join(file.name.split(".")[:-1]) + ".txt"
        text_content = ocr_core(file_path_jpg_crop + file.name)

        with open(file_path_pdf_cmp + file_name_txt, 'wb') as f:
            f.write(text_content.encode("utf-8-sig"))

        print(f"   -> took {round(time.time() - timestamp_start,2)} s")
