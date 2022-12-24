import os
import re
import tempfile
from typing import Any, Dict, List, Tuple, Union

import pandas as pd
import pdfplumber
import requests
from PIL import Image
from tqdm import tqdm


class NamedTemporaryPDF(object):
    """class that downloads pdf and makes it available as a named tempfile in a context manager"""

    def __init__(self, url: str):
        self.url = url
        self.temp_file_name = None

    def __enter__(self) -> str:
        response = requests.get(self.url)
        assert response.status_code == 200, f"Failed to download PDF from {self.url}"
        f = tempfile.NamedTemporaryFile(mode='wb', delete=False)
        f.write(response.content)
        self.temp_file_name = f.name
        return self.temp_file_name

    def __exit__(self, type, value, traceback):
        if self.temp_file_name:
            os.remove(self.temp_file_name)


# bad format for passing arguments to subfunctions, should refactor
def extract_all(
    pdf_path: str,
    prog_bar: bool = False,
    extract_images: bool = True,
    extract_text: bool = True,
    extract_words: bool = True,
    extract_tables: bool = True,
) -> Dict:
    """
    Extract data from a PDF file and return a dictionary with the extracted data.

    The `extract_all` function is a wrapper around the `pdfplumber.open` function, which returns a `PDF` object.
    The `PDF` object has a `pages` attribute, which is a list of `Page` objects. Each `Page` object has a number
    of methods for extracting data from the page.

    The returned dictionary will contain the following keys, depending on the input arguments:
        - 'images': a list of dictionaries, each of which contains the image data and bounding box coordinates
        - 'text': a list of strings, each of which is a line of text
        - 'words': a pandas DataFrame, each row of which is a word and its bounding box coordinates
        - 'tables': a list of pandas DataFrames, each of which is a table extracted from the PDF
        - 'lines': a pandas DataFrame, each row of which is a line of text and its bounding box coordinates

    Args:
        pdf_path: The path to the PDF file you want to extract from.
        prog_bar: Whether to show a progress bar. Defaults to False.
        extract_images: Whether to extract image data. Defaults to True.
        extract_text: Whether to extract text data. Defaults to True.
        extract_words: Whether to extract word data. Defaults to True.
        extract_tables: Whether to extract table data. Defaults to True.

    Returns:
        A dictionary with the keys 'images', 'text', 'words', 'tables', and 'lines'.
    """
    pdf = pdfplumber.open(pdf_path)
    images = []
    texts = []
    words = []
    tables = []
    lines = []
    if prog_bar:
        iterator = tqdm(pdf.pages)
    else:
        iterator = pdf.pages

    for page in iterator:
        if extract_images:
            for image in page.images:
                image_bbox = (image['x0'], image['top'], image['x1'], image['bottom'])
                image['image'] = page.crop(image_bbox).to_image(resolution=300).annotated
                images.append(image)

        if extract_text:
            texts += page.extract_text()

        if extract_words:
            _words = page.extract_words()
            for word in _words:
                word['page_number'] = page.page_number
            words += _words

        if extract_tables:
            tables += page.extract_tables()

    if extract_images:
        images = splice_images(images)
        images = order_images(images)

    if extract_words:
        words = pd.DataFrame(words)
        lines = word_df_to_line_df(words)

    if extract_words and extract_images:
        images = find_candidate_labels_for_figures(images, lines)

    return {'images': images, 'text': texts, 'words': words, 'tables': tables, 'lines': lines}


def identify_images_to_vertically_splice(image_list: List[dict]) -> List[Tuple[dict, dict]]:
    """Identifies images to vertically splice.
    Candidate images will be on the same page, have the same width, and the top of one image will be the bottom of the other image. Works for N images"""
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


def identify_images_to_horizontally_splice(image_list: List[Dict]) -> List[Tuple[Dict, Dict]]:
    """Identifies images to horizontally splice. Candidate images will be on the same page, have the same height, and the left of one image will be the right of the other image. Works for N images"""
    candidates: List[Tuple[Dict, Dict]] = []
    for i, image1 in enumerate(image_list):
        for j, image2 in enumerate(image_list):
            if i == j:
                continue
            if image1['page_number'] == image2['page_number']:
                if abs(image1['height'] - image2['height']) < 1:
                    if abs(image1['x1'] - image2['x0']) < 1:
                        candidates.append((image1, image2))
    return candidates


def vertically_splice_image_pair(top_image: Dict, bottom_image: Dict) -> Dict:
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

    # create new image and paste the images
    new_image['image'] = Image.new('RGB', (top_image_width, top_image_height + bottom_image_height))
    new_image['image'].paste(top_image['image'], (0, 0))
    new_image['image'].paste(bottom_image['image'], (0, top_image_height))

    return new_image


def horizontally_splice_image_pair(left_image: dict, right_image: dict) -> dict:
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


def splice_images(image_list: List) -> List:
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


def word_df_to_line_df(word_df: pd.DataFrame) -> pd.DataFrame:
    """Convert a dataframe of words to a dataframe of lines.

    The input dataframe should contain the following columns:
        - page_number: an integer representing the page number of the word
        - top: a float representing the top position of the word on the page (in some unit of measurement)
        - bottom: a float representing the bottom position of the word on the page (in some unit of measurement)
        - x0: a float representing the left position of the word on the page (in some unit of measurement)
        - text: a string representing the text of the word

    This function groups the words by page number and top/bottom position, sorts the words within each group by x0 position,
    and then joins the text of the words in each group to create a single line of text. A line number is also added to
    the output dataframe.

    The output dataframe will contain the following columns:
        - line_number: an integer representing the line number (starting from 0)
        - page_number: an integer representing the page number of the line
        - top: a float representing the top position of the line on the page (in some unit of measurement)
        - bottom: a float representing the bottom position of the line on the page (in some unit of measurement)
        - text: a string representing the text of the line

    Args:
        word_df: a pandas dataframe containing the word data

    Returns:
        a pandas dataframe containing the line data
    """
    line_df = (
        word_df.groupby(['page_number', 'top', 'bottom'], group_keys=True)
        .apply(lambda x: x.sort_values('x0'))
        .reset_index(drop=True)
        .groupby(['page_number', 'top', 'bottom'], group_keys=True)
        .apply(lambda x: ' '.join(x['text']))
        .rename('text')
        .reset_index()
        .reset_index()
        .rename(columns={'index': 'line_number'})
    )
    return line_df


def order_images(image_list: List) -> List:
    """Order a list of images by page number and then by y0, x0 positions.

    The input list should contain dictionaries representing images, with the following keys:
        - page_number: an integer representing the page number of the image
        - y0: a float representing the top position of the image on the page (in some unit of measurement)
        - x0: a float representing the left position of the image on the page (in some unit of measurement)

    This function sorts the images in the input list by page number and then by y0 and x0 positions, and adds an
    image number to each image dictionary.

    The output list will contain dictionaries with the following keys:
        - image_number: an integer representing the image number (starting from 1)
        - page_number: an integer representing the page number of the image
        - y0: a float representing the top position of the image on the page (in some unit of measurement)
        - x0: a float representing the left position of the image on the page (in some unit of measurement)

    Args:
        image_list: a list of dictionaries representing images

    Returns:
        a list of dictionaries representing the ordered images
    """
    ordered_image_list = sorted(image_list, key=lambda x: (x['page_number'], x['y0'], x['x0']))
    for ii, image in enumerate(ordered_image_list):
        image['image_number'] = ii + 1
    return ordered_image_list


def get_distance_from_line_to_image(line, image):
    """Calculate the minimum distance from a line to an image.

    The input 'line' should be a dictionary with the following keys:
        - top: a float representing the top position of the line on the page (in some unit of measurement)
        - bottom: a float representing the bottom position of the line on the page (in some unit of measurement)

    The input 'image' should be a dictionary with the following keys:
        - top: a float representing the top position of the image on the page (in some unit of measurement)
        - bottom: a float representing the bottom position of the image on the page (in some unit of measurement)

    This function calculates the y-coordinate of the center of the line, and then returns the minimum of the distances
    from the center of the line to the top and bottom of the image. If the center of the line is inside the image,
    the function returns 0.

    Args:
        line: a dictionary representing a line
        image: a dictionary representing an image

    Returns:
        a float representing the minimum distance from the line to the image
    """
    line_y_center = (line['top'] + line['bottom']) / 2
    if line_y_center > image['top'] and line_y_center < image['bottom']:
        return 0
    else:
        return min(abs(line_y_center - image['top']), abs(line_y_center - image['bottom']))


FIGURE_INDICATORS = ['figure', 'fig', 'fig.']


def extract_figure_labels(image: Dict[str, Any], lines: pd.DataFrame) -> List[Dict[str, Any]]:
    """Extract figure labels from a list of lines near an image.

    The input 'image' should be a dictionary with the following keys:
        - page_number: an integer representing the page number of the image

    The input 'lines' should be a pandas dataframe with the following columns:
        - page_number: an integer representing the page number of the line
        - top: a float representing the top position of the line on the page (in some unit of measurement)
        - bottom: a float representing the bottom position of the line on the page (in some unit of measurement)
        - text: a string representing the text of the line

    This function extracts lines from the input 'lines' dataframe that are on the same page as the 'image' and within
    a certain distance of the image. It then searches for figure labels in these lines, using the list of figure
    indicators stored in the global variable `FIGURE_INDICATORS`. If a figure label is found, a dictionary containing
    the page number, line number, word number, distance from the image, and label is added to the output list of labels.

    Args:
        image: a dictionary representing an image
        lines: a pandas dataframe containing line data

    Returns:
        a list of dictionaries containing figure labels and their positions
    """
    page_lines = lines[lines['page_number'] == image['page_number']].copy()
    page_lines['distance'] = page_lines.apply(
        lambda x: get_distance_from_line_to_image(x, image), axis=1
    )

    # add lines from next page if they are close enough. adjust distance to account for page height
    next_page_lines = lines[lines['page_number'] == image['page_number'] + 1].copy()
    page_height = page_lines['bottom'].max()
    next_page_lines['top'] = next_page_lines['top'] + page_height
    next_page_lines['bottom'] = next_page_lines['bottom'] + page_height
    next_page_lines['distance'] = next_page_lines.apply(
        lambda x: get_distance_from_line_to_image(x, image), axis=1
    )
    page_lines = pd.concat([page_lines, next_page_lines])

    figure_lines = page_lines[
        page_lines['text'].str.lower().str.contains('|'.join(FIGURE_INDICATORS))
    ]

    labels = []
    for _, row in figure_lines.iterrows():
        words = row['text'].lower().split()
        for ii, word in enumerate(words):
            word = ''.join([c for c in word if c.isalnum()])
            if word in FIGURE_INDICATORS:
                if ii < len(words) - 1:
                    label = words[ii + 1]
                    # remove any non-alphanumeric characters
                    label = ''.join([c for c in label if c.isalnum()])
                    if len(label) > 2:
                        label = label[:2]
                    labels.append(
                        {
                            'page_number': row['page_number'],
                            'line_number': row['line_number'],
                            'word_number': ii,
                            'distance': row['distance'],
                            'label': label,
                        }
                    )
    return labels


def find_candidate_labels_for_figures(
    images: List[Dict[str, Union[str, pd.DataFrame]]], lines: pd.DataFrame
) -> List[Dict[str, Union[str, pd.DataFrame]]]:
    """
    It takes a list of images and a dataframe of lines, and for each image, it extracts the candidate
    labels from the lines

    Args:
      images (List[Dict[str, Union[str, pd.DataFrame]]]): List[Dict[str, Union[str, pd.DataFrame]]]
      lines (pd.DataFrame): a dataframe of lines

    Returns:
      A list of dictionaries, where each dictionary contains the image name, the image dataframe, and
    the candidate labels dataframe.
    """
    for image in images:
        image['candidate_labels'] = pd.DataFrame(extract_figure_labels(image, lines))
    return images
