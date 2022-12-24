import os
import tempfile
from typing import Dict, List, Union

import pandas as pd
import pdfplumber
import requests
from PIL import Image
from tqdm import tqdm


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


def extract_all(
    pdf_path,
    prog_bar=False,
    extract_images: bool = True,
    extract_texts: bool = True,
    extract_words: bool = True,
    extract_tables: bool = True,
):
    pdf = pdfplumber.open(pdf_path)
    images = []
    texts = []
    words = []
    tables = []
    if prog_bar:
        iterator = tqdm(pdf.pages)
    else:
        iterator = pdf.pages
    if extract_images:
        for page in iterator:
            for image in page.images:
                image_bbox = (image['x0'], image['top'], image['x1'], image['bottom'])
                image['image'] = page.crop(image_bbox).to_image(resolution=300).annotated
                images.append(image)

            if extract_texts:
                texts += page.extract_text()

            if extract_words:
                _words = page.extract_words()
                for word in _words:
                    word['page_number'] = page.page_number
                words += _words

            if extract_tables:
                tables += page.extract_tables()

        images = splice_images(images)

    return {'images': images, 'texts': texts, 'words': pd.DataFrame(words), 'tables': tables}


def identify_images_to_vertically_splice(image_list):
    """Identifies images to vertically splice. Candidate images will be on the same page, have the same width, and the top of one image will be the bottom of the other image. Works for N images"""
    candidates = []
    for i, image1 in enumerate(image_list):
        for j, image2 in enumerate(image_list):
            if i == j:
                continue
            if image1['page_number'] == image2['page_number']:
                if abs(image1['width'] - image2['width']) < 1:
                    if abs(image1['top'] - image2['bottom']) < 1:
                        candidates.append((image2, image1))

    return candidates


def identify_images_to_horizontally_splice(image_list):
    """Identifies images to horizontally splice. Candidate images will be on the same page, have the same height, and the left of one image will be the right of the other image. Works for N images"""
    candidates = []
    for i, image1 in enumerate(image_list):
        for j, image2 in enumerate(image_list):
            if i == j:
                continue
            if image1['page_number'] == image2['page_number']:
                if abs(image1['height'] - image2['height']) < 1:
                    if abs(image1['x1'] - image2['x0']) < 1:
                        candidates.append((image1, image2))
    return candidates


def vertically_splice_image_pair(top_image, bottom_image):
    """Vertically splices two images. Returns a single dictionary for the new image"""
    new_image = top_image.copy()
    new_image['y0'] = bottom_image['y0']
    new_image['y1'] = top_image['y1']
    new_image['height'] = new_image['height'] + new_image['height']
    new_image['top'] = top_image['top']
    new_image['bottom'] = bottom_image['bottom']
    new_image['doctop'] = bottom_image['doctop']

    # get height and width from images directly since the values in the dictionary are in a different coordinate frame
    top_image_height = top_image['image'].height
    top_image_width = top_image['image'].width
    bottom_image_height = bottom_image['image'].height
    bottom_image_width = bottom_image['image'].width

    # create new image and paste the images
    new_image['image'] = Image.new('RGB', (top_image_width, top_image_height + bottom_image_height))
    new_image['image'].paste(top_image['image'], (0, 0))
    new_image['image'].paste(bottom_image['image'], (0, top_image_height))

    return new_image


def horizontally_splice_image_pair(left_image, right_image):
    """Horizontally splices two images. Returns a single dictionary for the new image"""
    new_image = left_image.copy()
    new_image['x0'] = left_image['x0']
    new_image['x1'] = right_image['x1']
    new_image['width'] = left_image['width'] + right_image['width']

    # get height and width from images directly since the values in the dictionary are in a different coordinate frame
    left_image_height = left_image['image'].height
    left_image_width = left_image['image'].width
    right_image_height = right_image['image'].height
    right_image_width = right_image['image'].width

    # create new image and paste the images
    new_image['image'] = Image.new('RGB', (left_image_width + right_image_width, left_image_height))
    new_image['image'].paste(left_image['image'], (0, 0))
    new_image['image'].paste(right_image['image'], (left_image_width, 0))

    return new_image


def splice_images(image_list):
    """Identifies sets of images to vertically splice and then splices them.
    For cases where images are split into N pieces, it iteratively merges them until there is one image"""
    new_image_list = image_list.copy()
    candidates = identify_images_to_vertically_splice(new_image_list)
    while len(candidates) > 0:
        candidate = candidates[0]
        new_image = vertically_splice_image_pair(candidate[0], candidate[1])
        new_image_list.append(new_image)
        if candidate[0] in new_image_list:
            new_image_list.remove(candidate[0])
        if candidate[1] in new_image_list:
            new_image_list.remove(candidate[1])
        candidates = identify_images_to_vertically_splice(new_image_list)

    candidates = identify_images_to_horizontally_splice(new_image_list)
    while len(candidates) > 0:
        candidate = candidates[0]
        new_image = horizontally_splice_image_pair(candidate[0], candidate[1])
        new_image_list.append(new_image)
        if candidate[0] in new_image_list:
            new_image_list.remove(candidate[0])
        if candidate[1] in new_image_list:
            new_image_list.remove(candidate[1])
        candidates = identify_images_to_horizontally_splice(new_image_list)
    return new_image_list
