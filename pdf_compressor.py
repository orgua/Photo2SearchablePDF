"""
author: Pure Python
url: https://www.purepython.org
copyright: CC BY-NC 4.0
Forked date: 2018-01-07 / First version MIT license -- free to use as you want, cheers.

Original Author: Sylvain Carlioz, 6/03/2017

Simple python wrapper script to use ghoscript function to compress PDF files.
With this class you can compress and or fix a folder with (corrupt) PDF files.

You can also use this class within your own scripts just do a
import CompressPDF

Compression levels:
    0: default
    1: prepress
    2: printer
    3: ebook
    4: screen

Dependency: Ghostscript.
On MacOSX install via command line `brew install ghostscript`.
"""

import argparse
import subprocess
import sys
from pathlib import Path


class CompressPDF:
    def __init__(
        self, compress_level: int = 0, ghostscript_path: str = None, *, show_info: bool = False
    ) -> None:
        self.compress_level = compress_level

        if ghostscript_path is None:
            self.gs_path = "gs"
        else:
            self.gs_path = ghostscript_path

        self.quality = {0: "/default", 1: "/prepress", 2: "/printer", 3: "/ebook", 4: "/screen"}

        self.show_compress_info = show_info

    def compress(self, file_path_in: Path, file_path_out: Path, page_size_mm: tuple | None = None):
        """
        Function to compress PDF via Ghostscript command line interface
        :param page_size_mm: dimensions width * height in mm
        :param file_path_in: old file that needs to be compressed
        :param file_path_out: new file that is compressed
        :return: True or False, to do a cleanup when needed
        """
        try:
            if not file_path_in.exists() or not file_path_in.is_file():
                print("Error: invalid path for input PDF file")
                sys.exit(1)

            # Check if file is a PDF by extension
            if file_path_in.suffix.lower() != ".pdf":
                raise Exception("Error: input file is not a PDF")

            pre_opt = [
                self.gs_path,
                "-sDEVICE=pdfwrite",
                f"-dPDFSETTINGS={self.quality[self.compress_level]}",
                "-dCompatibilityLevel=1.7",
                "-dNOPAUSE",
                "-dQUIET",
                "-dBATCH",
            ]

            # Proper PDF Controls and Features: https://www.ghostscript.com/doc/current/VectorDevices.htm
            # -dColorConversionStrategy=/Gray -dProcessColorModel=/DeviceGray
            # -dPrinted=false -> Preserve hyperlinks
            # TODO: switch to do black/white
            if page_size_mm is not None:
                pre_opt += [
                    f"-dDEVICEWIDTHPOINTS={round(page_size_mm[0] * 72 / 25.4)}",
                    f"-dDEVICEHEIGHTPOINTS={round(page_size_mm[1] * 72 / 25.4)}",
                    "-dPDFFitPage",
                ]

            subprocess.call(pre_opt + [f"-sOutputFile={file_path_out}", file_path_in])

            if self.show_compress_info:
                initial_size = file_path_in.stat().st_size
                final_size = file_path_out.stat().st_size
                ratio = 1 - (final_size / initial_size)
                print(f"Compression by {ratio:.0%}.")
                print(f"Final file size is {final_size / 1000000:.1f}MB")

            return True
        except Exception as error:
            print("Caught this error: " + repr(error))
        except subprocess.CalledProcessError:
            print("Unexpected error:")
            return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""Welcome to this helpfile. """, epilog="""That's all folks!"""
    )
    parser.add_argument(
        "-sf", "--startFolder", help="Start Folder Domain", required=False, type=str
    )
    parser.add_argument(
        "-cl", "--compressLevel", type=int, help="Compression level from 0 to 4", default=2
    )
    parser.add_argument(
        "-s", "--showInfo", type=int, help="Show extra compression information 0 or 1", default=0
    )
    args = parser.parse_args()

    """when where is no start folder full stop!"""
    if args.startFolder is not None and args.startFolder != "":
        start_folder = Path(args.startFolder)

        p = CompressPDF(args.compressLevel)

        compress_folder = start_folder.absolute() / "compressed_folder"
        if not compress_folder.exists():
            compress_folder.mkdir(parents=True, exist_ok=True)

        """Loop within folder over PDF files"""
        for file_old in start_folder.iterdir():
            if file_old.suffix.lower() == ".pdf":
                new_file = compress_folder / file_old.name

                if p.compress(file_old, new_file):
                    print(f"{file_old.name} done!")
                else:
                    print(f"{file_old} gave an error!")
