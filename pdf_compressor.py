#!/usr/bin/env python3

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
import subprocess
import os.path
import sys
import argparse


class CompressPDF:

    def __init__(self, compress_level=0, ghostscript_path: str = None, show_info=False):
        self.compress_level = compress_level

        if ghostscript_path is None:
            self.gs_path = "gs"
        else:
            self.gs_path = ghostscript_path

        self.quality = {
            0: '/default',
            1: '/prepress',
            2: '/printer',
            3: '/ebook',
            4: '/screen'
        }

        self.show_compress_info = show_info

    def compress(self, file_path_in=None, file_path_out=None, page_size_mm: tuple = None):
        """
        Function to compress PDF via Ghostscript command line interface
        :param page_size_mm: dimensions width * height in mm
        :param file_path_in: old file that needs to be compressed
        :param file_path_out: new file that is commpressed
        :return: True or False, to do a cleanup when needed
        """
        try:
            if not os.path.isfile(file_path_in):
                print("Error: invalid path for input PDF file")
                sys.exit(1)

            # Check if file is a PDF by extension
            filename, file_extension = os.path.splitext(file_path_in)
            if file_extension != '.pdf':
                raise Exception("Error: input file is not a PDF")
                return False

            if self.show_compress_info:
                initial_size = os.path.getsize(file_path_in)

            pre_opt = [self.gs_path,
                       '-sDEVICE=pdfwrite',
                       '-dCompatibilityLevel=1.4',
                       '-dPDFSETTINGS={}'.format(self.quality[self.compress_level]),
                       '-dNOPAUSE',
                       '-dQUIET',
                       '-dBATCH']

            if page_size_mm is not None:
                pre_opt += [f'-dDEVICEWIDTHPOINTS={round(page_size_mm[0] * 72 / 25.4)}',
                            f'-dDEVICEHEIGHTPOINTS={round(page_size_mm[1] * 72 / 25.4)}',
                            '-dPDFFitPage']

            subprocess.call(pre_opt + ['-sOutputFile={}'.format(file_path_out), file_path_in])

            if self.show_compress_info:
                final_size = os.path.getsize(file_path_out)
                ratio = 1 - (final_size / initial_size)
                print("Compression by {0:.0%}.".format(ratio))
                print("Final file size is {0:.1f}MB".format(final_size / 1000000))

            return True
        except Exception as error:
            print('Caught this error: ' + repr(error))
        except subprocess.CalledProcessError as e:
            print("Unexpected error:".format(e.output))
            return False


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='''Welcome to this helpfile. ''',
        epilog="""Thats all folks!""")
    parser.add_argument('-sf', '--startFolder', help='Start Folder Domain', required=False, type=str)
    parser.add_argument('-cl', '--compressLevel', type=int, help='Compression level from 0 to 4', default=2)
    parser.add_argument('-s', '--showInfo', type=int, help='Show extra compression information 0 or 1', default=0)
    args = parser.parse_args()

    '''when where is no start folder full stop!'''
    if args.startFolder is not None and args.startFolder != "":
        start_folder = args.startFolder

        p = CompressPDF(args.compressLevel)

        compress_folder = os.path.join(start_folder, "compressed_folder/")
        if not os.path.exists(compress_folder):
            os.makedirs(compress_folder)

        '''Loop within folder over PDF files'''
        for filename in os.listdir(args.startFolder):
            my_name, file_extension = os.path.splitext(filename)
            if file_extension == '.pdf':
                file = os.path.join(start_folder, filename)
                new_file = os.path.join(compress_folder, filename)

                if p.compress(file, new_file):
                    print("{} done!".format(filename))
                else:
                    print("{} gave an error!".format(file))
