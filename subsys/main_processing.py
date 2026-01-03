import signal
import sys
import time
from collections.abc import Iterable
from collections.abc import Sequence
from dataclasses import dataclass
from multiprocessing import Pool
from pathlib import Path
from types import FrameType

from tqdm import tqdm

from .date_extraction import extract_date
from .image_ocr import ImageOCR
from .keyword_extraction import extract_keywords
from .logger import increase_verbose_level
from .logger import log

image_suffixes = [".jpg", ".jpeg", ".bmp", ".png", ".tif"]


@dataclass(kw_only=True, frozen=True)
class ImageProcessorConfig:
    __slots__ = ()

    path: Path

    save_text: bool = True
    save_pdf: bool = True
    save_meta: bool = False

    lang_ids: list[str] | str | None = None
    """ limit detected languages, TODO: really needed?

    - ISO 639-1 language codes (2 letters)
    - use one or list of many
    - disabled if None (use all available languages)
     """
    lang_id_default: str = "en"


def exit_gracefully(_signum: int, _frame: FrameType | None) -> None:
    log.warning("Exiting!")
    sys.exit(0)


def get_images(path: Path, *, recurse: bool = False) -> list[Path]:
    files: list[Path] = []
    if path.is_file() and path.suffix.lower() in image_suffixes:
        files = [path]
    elif path.is_dir():
        files = [x for x in path.iterdir() if x.is_file() and x.suffix.lower() in image_suffixes]
    if recurse:
        raise NotImplementedError
    return files


class ImageProcessor:
    def __init__(self, cfg: ImageProcessorConfig) -> None:
        self.cfg = cfg

    def process_file(self, path: Path) -> None:
        path_pdf = path.with_suffix(".pdf")
        path_text = path.with_suffix(".txt")
        path_meta = path.with_suffix(".yaml")

        need_pdf = self.cfg.save_pdf and not path_pdf.exists()
        need_text = self.cfg.save_text and not path_text.exists()
        need_meta = self.cfg.save_meta and not path_meta.exists()

        if not (need_pdf or need_text or need_meta):
            return

        log.debug(f"processing {path.name}")
        ocr = ImageOCR(path)
        lang_id = ocr.detect_lang_id()  # TODO: add lang_ids config and default lang
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

    def _process_sp(self, files: Iterable[Path]) -> None:
        increase_verbose_level(3)
        for file in tqdm(files, desc="OCR Images", unit="n", leave=False):
            self.process_file(file)

    def _process_mp(self, files: Sequence[Path]) -> None:
        with Pool() as pool:
            log.info(f"Multiprocessing with {pool._processes} workers")

            def exit_pool(_signum: int, _frame: FrameType | None) -> None:
                pool.terminate()
                log.warning("Exiting!")
                sys.exit(0)

            signal.signal(signal.SIGTERM, exit_pool)
            signal.signal(signal.SIGINT, exit_pool)

            progress_bar = tqdm(
                total=len(files),
                desc="OCR Images",
                unit="n",
                leave=False,
            )

            for _ in pool.imap(self.process_file, files):
                progress_bar.update(n=1)

    def process(self, *, multiprocess: bool = True) -> None:
        signal.signal(signal.SIGTERM, exit_gracefully)
        signal.signal(signal.SIGINT, exit_gracefully)

        timestamp_start = time.time()
        files = get_images(self.cfg.path)

        if multiprocess:
            self._process_mp(files)
        else:
            self._process_sp(files)
        # TODO: join multi-pdf
        log.debug(f"\t-> processing took {round(time.time() - timestamp_start, 2)} s")
