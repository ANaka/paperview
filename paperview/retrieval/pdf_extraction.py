import os
import tempfile
from io import BytesIO, StringIO
from typing import Dict, List, Union

import PyPDF2
import requests
from pdfminer.converter import PDFPageAggregator, TextConverter
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams, LTChar, LTFigure, LTImage, LTTextBox, LTTextLine
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage, PDFTextExtractionNotAllowed
from pdfminer.pdfparser import PDFParser
from pikepdf import Pdf, PdfImage
from PIL import Image, UnidentifiedImageError


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


# def extract_images(pdf_path: str) -> List[Dict[str, Union[int, str, PdfImage]]]:
#     # Extracts images from a PDF file and returns them as a list of dictionaries.
#     # Each dictionary contains the page number, the name of the image, and the image itself.
#     doc = Pdf.open(pdf_path)
#     images = []
#     for ii, page in enumerate(doc.pages):
#         for jj, (name, raw_image) in enumerate(page.images.items()):
#             image = PdfImage(raw_image)
#             images.append(
#                 {
#                     'page': ii,
#                     'name': name,
#                     'image': image,
#                 }
#             )

#     return images


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


def _extract_text_to_fp(
    pdf_path: str,
    output_type='html',
    codec=None,
    laparams_kwargs=None,
    bytes_output: bool = False,
    **kwargs,
) -> str:
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
    laparams_kwargs = {} if laparams_kwargs is None else laparams_kwargs
    laparams = LAParams(**laparams_kwargs)
    if bytes_output:
        layout_output = BytesIO()
    else:
        layout_output = StringIO()
    with open(pdf_path, 'rb') as fin:
        extract_text_to_fp(
            fin, layout_output, laparams=laparams, output_type=output_type, codec=codec, **kwargs
        )

        layout_text = layout_output.getvalue()
    if bytes_output:
        layout_text = layout_text.decode('utf-8')

    return layout_text


def extract_outlines(pdf_path: str) -> List[Dict[str, Union[int, str]]]:
    """
    > We open the PDF file, create a parser, create a PDF document, and then loop through the outlines
    of the PDF document and extract the title, page number, and level of each outline.

    Args:
      pdf_path (str): The path to the PDF file you want to extract outlines from.

    Returns:
      A list of dictionaries, where each dictionary contains the title, page number, and level of each
      outline.
    """
    outlines = []
    with open(pdf_path, 'rb') as in_file:
        parser = PDFParser(in_file)
        doc = PDFDocument(parser)
        for (level, title, dest, a, se) in doc.get_outlines():
            outlines.append(
                {
                    'title': title,
                    'page': dest[0].objid,
                    'level': level,
                }
            )

    return outlines


def extract_layout(pdf_path: str):

    with open(pdf_path, 'rb') as in_file:
        parser = PDFParser(in_file)
        doc = PDFDocument(parser)
        # Check if the PDF is extractable
        if not doc.is_extractable:
            raise PDFTextExtractionNotAllowed
        rsrcmgr = PDFResourceManager()

        device = PDFPageAggregator(rsrcmgr, laparams=LAParams(all_texts=True, line_margin=0.5))
        interpreter = PDFPageInterpreter(rsrcmgr, device)

        data = []
        # Process each page of the PDF
        for page_number, page in enumerate(PDFPage.create_pages(doc)):
            interpreter.process_page(page)
            layout = device.get_result()
            data.append(
                {
                    'page': page_number,
                    'type': type(layout).__name__,
                    'x0': layout.x0,
                    'y0': layout.y0,
                    'x1': layout.x1,
                    'y1': layout.y1,
                }
            )

            for obj in layout:
                _data = {
                    'page': page_number,
                    'type': type(obj).__name__,
                    'x0': obj.x0,
                    'y0': obj.y0,
                    'x1': obj.x1,
                    'y1': obj.y1,
                }
                if hasattr(obj, "get_text"):
                    _data['text'] = obj.get_text()
                data.append(_data)

    return data


def extract_images(pdf_path):
    """
    > We open the PDF file, create a parser, create a PDF document, and then loop through the pages of
    the PDF document and extract the images on each page.

    Args:
      pdf_path (str): The path to the PDF file you want to extract images from.

    Returns:
      A list of dictionaries, where each dictionary contains the page number, bbox, and image data.
    """
    with open(pdf_path, 'rb') as file:
        # Create a PDF object
        pdf = PyPDF2.PdfFileReader(file)

        data = []
        # Iterate through all the pages
        for page_num in range(pdf.getNumPages()):
            # Get the current page
            page = pdf.getPage(page_num)

            # Extract all the images on the current page
            # if '/Resources' in page:
            resources = page.get('/Resources', None)

            try:
                xobject = resources['/XObject']
            except:
                xobject = None

            if xobject:
                images = xobject.getObject()
            else:
                images = {}

            # Iterate through all the images
            for img_name, img in images.items():
                img_data = img.getObject()

                # Check if the image is an image object
                if img_data['/Subtype'] != '/Image':
                    continue

                # Get the image dimensions and position on the page
                width = img_data['/Width']
                height = img_data['/Height']

                # Use the default position (0, 0) if the '/Matrix' key is not present
                x_pos = img_data.get('/Matrix', [1, 0, 0, 1, 0, 0])[4]
                y_pos = img_data.get('/Matrix', [1, 0, 0, 1, 0, 0])[5]

                # Calculate the bounding box of the image
                left = x_pos
                right = x_pos + width
                bottom = y_pos
                top = y_pos + height

                # Extract the image data and create a PIL Image instance
                image_data = img_data.getData()
                try:
                    image = Image.open(BytesIO(image_data))
                except UnidentifiedImageError:
                    image = None

                _data = {
                    'page': page_num,
                    'type': 'image',
                    'x0': left,
                    'y0': bottom,
                    'x1': right,
                    'y1': top,
                    'image': image,
                }
                data.append(_data)
    return data


# Define a function to check if two images have the same height or width
def match_dimensions(img1, img2):
    return img1['x1'] == img2['x1'] or img1['y1'] == img2['y1']


def merge_image_pieces(image_pieces):
    # Check if the image pieces have the same width or height
    same_width = all(piece['x1'] == image_pieces[0]['x1'] for piece in image_pieces)
    same_height = all(piece['y1'] == image_pieces[0]['y1'] for piece in image_pieces)

    if same_width | same_height:
        assert same_width != same_height, 'Cannot determine which dim to concatenate on'

    # Create an empty image with the appropriate size and mode
    if same_width:
        image_width = image_pieces[0]['x1']
        image_height = sum(piece['y1'] for piece in image_pieces)
        orientation = 'vertical'
    elif same_height:
        image_width = sum(piece['x1'] for piece in image_pieces)
        image_height = image_pieces[0]['y1']
        orientation = 'horizontal'
    else:
        raise ValueError('Cannot merge images with different dimensions')
    image = Image.new(mode='RGB', size=(image_width, image_height))

    # Iterate through the image pieces and paste them into the empty image
    if orientation == 'horizontal':
        x_offset = 0
        for piece in image_pieces:
            image.paste(piece['image'], (x_offset, 0))
            x_offset += piece['x1']
    elif orientation == 'vertical':
        y_offset = 0
        for piece in image_pieces:
            image.paste(piece['image'], (0, y_offset))
            y_offset += piece['y1']

    output = {
        'page': image_pieces[0]['page'],
        'type': 'image',
        'x0': image_pieces[0]['x0'],
        'y0': image_pieces[0]['y0'],
        'x1': image_width,
        'y1': image_height,
        'image': image,
    }
    return output


def identify_images_to_merge(images):
    sets_to_merge = []
    for i, img1 in enumerate(images):
        for img2 in images[i + 1 :]:
            if img1['page'] == img2['page'] and match_dimensions(img1, img2):
                already_in_set = any(img1 in set_to_merge for set_to_merge in sets_to_merge) or any(
                    img2 in set_to_merge for set_to_merge in sets_to_merge
                )
                if not already_in_set:
                    sets_to_merge.append([img1, img2])
                else:
                    set_to_add_to = None
                    for set_to_merge in sets_to_merge:
                        if img1 in set_to_merge:
                            set_to_add_to = set_to_merge
                            break
                        elif img2 in set_to_merge:
                            set_to_add_to = set_to_merge
                            break
                    if set_to_add_to:
                        set_to_add_to.append(img1 if img2 in set_to_add_to else img2)
    return sets_to_merge


def merge_images(images):
    # Identify the sets of images to merge
    sets_to_merge = identify_images_to_merge(images)

    # Remove the images that were merged from the list of images
    all_images_to_merge = []
    for x in sets_to_merge:
        all_images_to_merge += x

    pruned_images = [image for image in images if image not in all_images_to_merge]

    # Merge the images in each set
    merged_images = []
    for set_to_merge in sets_to_merge:
        merged_images.append(merge_image_pieces(set_to_merge))

    images = merged_images + pruned_images

    # sort the images by page number and then by y0 position
    images = sorted(images, key=lambda x: (x['page'], x['y0']))

    return images
