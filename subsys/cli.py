import sys
from importlib import metadata
from pathlib import Path

import typer

from .logger import increase_verbose_level
from .logger import log
from .main_processing import ImageProcessor
from .main_processing import activate_exit_handler

cli = typer.Typer(help="Web-Server & -API for the Shepherd-Testbed")

verbose_opt_t = typer.Option(
    False,  # noqa: FBT003
    "--verbose",
    "-v",
    help="Sets logging-level to debug",
)


@cli.callback()
def cli_callback(*, verbose: bool = verbose_opt_t) -> None:
    """Enable verbosity and add exit-handlers
    this gets executed prior to the other sub-commands
    """
    activate_exit_handler()
    increase_verbose_level(3 if verbose else 2)


@cli.command()
def version() -> None:
    """Prints version-infos (combinable with -v)"""
    log.info("photo2pdf v%s", metadata.version("photo2pdf"))
    log.debug("Python v%s", sys.version)

    for package in ["typer", "click", "pytesseract", "pillow"]:
        log.debug("%s v%s", package, metadata.version(package))


@cli.command()
def process(
    path: Path | None = None,
    *,
    save_text: bool = False,
    save_meta: bool = False,
    debug: bool = False,
) -> None:
    """OCR Images by either providing a directory, a file or none (use CWD).

    in addition to searchable PDFs, this tool can also
    - save the text content as .txt,
    - save metadata like keywords, language, etc.

    by switching on debug-mode multiprocessing is disabled (slower, more verbose, saves RAM)
    """
    if path is None:
        path = Path.cwd()
    ip = ImageProcessor(
        path=path,
        save_text=save_text,
        save_pdf=True,
        save_meta=save_meta,
    )
    ip.process(multiprocess=not debug)


if __name__ == "__main__":
    cli()
