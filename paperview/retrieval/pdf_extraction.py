import os
import tempfile
from io import StringIO
from typing import Dict, List, Union

import requests
from pdfminer.converter import TextConverter
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pikepdf import Pdf, PdfImage


class NamedTemporaryPDF(object):
    """class that downloads pdf and makes it available as a named tempfile in a context manager"""

    def __init__(self, url):
        self.url = url
        self.temp_file_name = None

    def __enter__(self):
        response = requests.get(self.url)
        assert response.status_code == 200, f"Failed to download PDF from {self.url}"
        f = tempfile.NamedTemporaryFile(mode='wb', delete=False)
        f.write(response.content)
        self.temp_file_name = f.name
        return self.temp_file_name

    def __exit__(self, type, value, traceback):
        if self.temp_file_name:
            os.remove(self.temp_file_name)


def extract_images(pdf_path: str) -> List[Dict[str, Union[int, str, PdfImage]]]:
    # Extracts images from a PDF file and returns them as a list of dictionaries.
    # Each dictionary contains the page number, the name of the image, and the image itself.
    doc = Pdf.open(pdf_path)
    images = []
    for ii, page in enumerate(doc.pages):
        for jj, (name, raw_image) in enumerate(page.images.items()):
            image = PdfImage(raw_image)
            images.append(
                {
                    'page': ii,
                    'name': name,
                    'image': image,
                }
            )

    return images


def extract_text(pdf_path: str) -> str:
    """
    > We open the PDF file, create a parser, create a PDF document, create a resource manager, create a
    device, create an interpreter, and then loop through the pages of the PDF and process them

    Args:
      pdf_path (str): The path to the PDF file you want to convert to text.

    Returns:
      A string of the text in the PDF
    """
    output_string = StringIO()
    with open(pdf_path, 'rb') as in_file:
        parser = PDFParser(in_file)
        doc = PDFDocument(parser)
        rsrcmgr = PDFResourceManager()
        device = TextConverter(rsrcmgr, output_string, laparams=LAParams())
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        for page in PDFPage.create_pages(doc):
            interpreter.process_page(page)

        text = output_string.getvalue()
    return text


def extract_html(pdf_path: str) -> str:
    """
    > We open the PDF file, and then we use the `extract_text_to_fp` function to extract the text from
    the PDF file and write it to a string buffer.

    The `extract_text_to_fp` function is a function from the `pdfminer.pdfinterp` module.

    The `extract_text_to_fp` function takes the following arguments:

    - `rsrcmgr`: A resource manager object.
    - `device`: A device object.
    - `pagenos`: A list of page numbers to extract.
    - `maxpages`: The maximum number of pages to extract.
    - `password`: The password to decrypt the PDF file.
    - `caching`: Whether to cache the decoded PDF file.
    - `check_extractable`: Whether to check if

    Args:
      pdf_path (str): the path to the PDF file you want to extract text from
    """
    layout_output_string = StringIO()
    with open(pdf_path, 'rb') as fin:
        extract_text_to_fp(
            fin, layout_output_string, laparams=LAParams(), output_type='html', codec=None
        )

        layout_text = layout_output_string.getvalue()
    return layout_text
