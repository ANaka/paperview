import base64
import datetime
import os
import re
import tempfile
import time
import urllib
import webbrowser
from io import BytesIO
from typing import Dict, List
from urllib.request import urlopen

import requests
from bs4 import BeautifulSoup
from IPython.core.display import HTML
from IPython.display import display
from PIL import Image
from pydantic import BaseModel, Field

from paperview.retrieval import pdf_extraction, process_xml

BASE_URL = "https://api.biorxiv.org"


class Message(BaseModel):
    status: str
    interval: str = None
    cursor: str = None
    count: int = None
    count_new_papers: int = None
    total: int = None

    def __repr__(self):
        return (
            f"Message(status='{self.status}', interval='{self.interval}', "
            f"cursor='{self.cursor}', count={self.count}, "
            f"count_new_papers={self.count_new_papers}, total={self.total})"
        )


def split_authors(authors: str) -> list:
    """Split a string of authors into a list of individual author names."""
    return authors.split("; ")


class ArticleDetail(BaseModel):
    title: str
    authors: list = Field(converter=split_authors)
    date: str
    category: str
    doi: str
    author_corresponding: str
    author_corresponding_institution: str
    version: str
    type: str
    license: str
    abstract: str
    published: str
    server: str
    jatsxml: str

    def __repr__(self):
        return f"""
ArticleDetail(
    title='{self.title}',
    authors={self.authors},
    date='{self.date}',
    category='{self.category}',
    doi='{self.doi}',
    author_corresponding='{self.author_corresponding}',
    author_corresponding_institution='{self.author_corresponding_institution}',
    version='{self.version}',
    type='{self.type}',
    license='{self.license}',
    abstract='{self.abstract}',
    published='{self.published}',
    server='{self.server}',
    jatsxml='{self.jatsxml}')"""

    @property
    def pdf_url(self):
        return f'https://www.biorxiv.org/content/{self.doi}v{self.version}.full.pdf'

    @classmethod
    def from_response(cls, response):
        data = response.json()["collection"]
        # assert len(data) == 1, f"Expected 1 item in response['collection'], got {len(data)}"
        data = data[0]
        return cls.from_collection_dict(data)

    @classmethod
    def from_collection_dict(cls, collection_dict):
        collection_dict['authors'] = collection_dict['authors'].split('; ')
        return cls(**collection_dict)

    def retrieve_jats_xml(self) -> str:
        """
        It takes an ArticleDetail object and returns the JATS XML for the article

        Returns:
          A string of JATS XML
        """
        return requests.get(self.jatsxml).text

    @property
    def base_xml_url(self):
        return self.jatsxml.split('.source.xml')[0]

    def get_image_url(self, slug: str):
        return f'{self.base_xml_url}/{slug}.large.jpg'

    def get_image(self, slug: str):
        url = self.get_image_url(slug)
        with urlopen(url) as response:
            with BytesIO(response.read()) as file:
                img = Image.open(file)
                img_data = img.tobytes()  # shenanigans to get it in memory while file is open
                return Image.frombytes(img.mode, img.size, img_data)


def _query_content_detail_by_doi(
    doi: str,
    server: str = "biorxiv",  # biorxiv or medRxiv
    format: str = "JSON",  # JSON or XML
) -> requests.models.Response:
    """https://api.biorxiv.org/details/[server]/[DOI]/na/[format] returns detail for a single manuscript.
    For instance, https://api.biorxiv.org/details/biorxiv/10.1101/339747 will output metadata for the biorxiv paper with DOI 10.1101/339747."""
    url = f"{BASE_URL}/details/{server}/{doi}/na/{format}"
    response = requests.get(url)
    return response


def get_content_detail_by_doi(
    doi: str,
    server: str = "biorxiv",  # biorxiv or medRxiv
    format: str = "JSON",  # JSON or XML
) -> ArticleDetail:
    response = _query_content_detail_by_doi(doi, server, format)
    return ArticleDetail.from_response(response)


def validate_interval(interval: str) -> bool:
    """
    Checks if the interval is a valid format for use in API requests.

    The interval can be 1) two YYYY-MM-DD dates separated by '/', 2) a numeric value for the N most recent posts,
    or 3) a numeric value with the letter 'd' for the most recent N days of posts.

    Args:
        interval (str): the interval to be checked

    Returns:
        bool: True if the interval is valid, False otherwise
    """
    # Check if the interval is a range of dates
    if re.match(r"\d{4}-\d{2}-\d{2}/\d{4}-\d{2}-\d{2}", interval):
        start, end = interval.split("/")
        try:
            start_date = datetime.datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.datetime.strptime(end, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    # Check if the interval is a numeric value for the N most recent posts
    if re.match(r"^\d+$", interval):
        return True

    # Check if the interval is a numeric value with the letter 'd' for the most recent N days of posts
    if re.match(r"\d+d", interval):
        return True

    return False


def query_content_detail_by_interval(
    interval: str,
    cursor: int = 0,
    server: str = "biorxiv",  # biorxiv or medRxiv
    format: str = "JSON",  # JSON or XML
):
    """
    > This function returns a dictionary with two keys: `messages` and `collections`. The `messages` key
    contains a list of `Message` objects, and the `collections` key contains a list of `ArticleDetail`
    objects

    Args:
      interval (str): str, the interval to query. Can be a date range, a number of days, or a number of
    articles.
      cursor (int): The starting point for the query. Defaults to 0. Defaults to 0
      server (str): biorxiv or medRxiv. Defaults to biorxiv
      format (str): JSON or XML. Defaults to JSON

    Returns:
      A dictionary with two keys: messages and collections.

    The format of the endpoint is https://api.biorxiv.org/details/[server]/[interval]/[cursor]/[format] or https://api.biorxiv.org/details/[server]/[DOI]/na/[format]
    where 'interval' can be 1) two YYYY-MM-DD dates separted by '/' and 'cursor' is the start point which defaults to 0 if not supplied, or 2) a numeric value for the N most recent posts, or 3) a numeric with the letter 'd' for the most recent N days of posts.
    Where metadata for multiple papers is returned, results are paginated with 100 papers served in a call. The 'cursor' value can be used to iterate through the result.
    For instance, https://api.biorxiv.org/details/biorxiv/2018-08-21/2018-08-28/45 will output 100 results (if that many remain) within the date range of 2018-08-21 to 2018-08-28 beginning from result 45 for biorxiv.
    """
    if not validate_interval(interval):
        raise ValueError(f"Invalid interval: {interval}")
    url = f"{BASE_URL}/details/{server}/{interval}/{cursor}/{format}"
    response = requests.get(url)
    # Parse the messages output
    messages = response.json()["messages"]
    parsed_messages = [Message(**message) for message in messages]

    # Parse the collections output
    collections = response.json()["collection"]
    parsed_collections = [
        ArticleDetail.from_collection_dict(collection) for collection in collections
    ]

    # Return the parsed messages and collections
    return {"messages": parsed_messages, "collections": parsed_collections}


def get_all_content_details_by_interval(
    interval: str, server: str = "bioRxiv", format: str = "json"
) -> List[ArticleDetail]:
    """
    It takes a date interval, and returns a list of all the articles in that interval

    Args:
        interval (str): The interval of time to query. This can be one of the following:
        server (str): The server to query. This can be either "bioRxiv" or "medRxiv". Defaults to bioRxiv
        format (str): The format of the response. Can be json or xml. Defaults to json

    Returns:
        A list of dictionaries.
    """
    all_results = []
    cursor = 0
    while True:
        results = query_content_detail_by_interval(
            interval, cursor=cursor, server=server, format=format
        )
        collections = results["collections"]
        all_results.extend(collections)
        if len(collections) < 100:
            # There are no more pages of results
            break
        cursor += 100
    return all_results


def query_article_by_doi(doi: str, server: str = "biorxiv", format: str = "JSON"):
    """https://api.biorxiv.org/pubs/[server]/[DOI]/na/[format] returns detail for a single manuscript.
    For instance, https://api.biorxiv.org/pubs/medrxiv/10.1101/2021.04.29.21256344 will output publication metadata for the biorxiv paper with DOI 10.1101/2021.04.29.21256344. Conversely, https://api.biorxiv.org/pubs/medrxiv/10.1371/journal.pone.0256482 will output publication metadata for the medRxiv paper with published DOI 10.1371/journal.pone.0256482.url = f"{BASE_URL}/details/{server}/{doi}/na/{format}"""
    url = f"{BASE_URL}/pubs/{server}/{doi}/na/{format}"
    response = requests.get(url)
    return response


def get_doi_from_page(url: str) -> str:
    """
    It takes a URL, finds the DOI, and then queries the API for the article details

    Args:
        url (str): The URL of the article you want to get the metadata for.

    Returns:
        A DOI
    """
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')

    doi_element = soup.find(class_='highwire-cite-metadata-doi highwire-cite-metadata')
    doi_url = doi_element.get_text()
    return doi_url.split("https://doi.org/")[-1].strip()


def get_content_detail_for_page(url: str) -> ArticleDetail:
    """
    It takes a URL, finds the DOI, and then queries the API for the article details

    Args:
        url (str): The URL of the article you want to get the metadata for.

    Returns:
        ArticleDetail
    """
    return get_content_detail_by_doi(get_doi_from_page(url))


class Article(object):
    def __init__(
        self,
        article_detail: ArticleDetail,
        extract_images: bool = True,
        extract_text_from_pdf: bool = True,
        extract_words_from_pdf: bool = True,
        extract_tables_from_pdf: bool = None,
        resolution: int = 300,
        **kwargs,
    ):
        self.article_detail = article_detail

        self.xml = self.article_detail.retrieve_jats_xml()
        self.data = process_xml.extract_all(self.xml)

        self.full_xml_retrieved = (self.data['all_text']['title'] == 'Results').any()

        if self.full_xml_retrieved:
            images = []
            for ii, row in self.data['figure_captions'].iterrows():
                slug = f'F{ii + 1}'
                image_data = row.to_dict()
                image_data['slug'] = slug
                image_data['image'] = self.article_detail.get_image(slug)
                images.append(image_data)
            self.data['images'] = images
        else:
            with pdf_extraction.NamedTemporaryPDF(self.article_detail.pdf_url) as f:
                _data = pdf_extraction.extract_all(
                    f,
                    extract_images=extract_images,
                    extract_text=extract_text_from_pdf,
                    extract_words=extract_words_from_pdf,
                    extract_tables=extract_tables_from_pdf,
                    resolution=resolution,
                    **kwargs,
                )
                self.data.update(_data)

    def __repr__(self):
        return f"""
Article(
    title='{self.article_detail.title}',
    authors={';'.join(self.article_detail.authors)},
    date='{self.article_detail.date}',
    category='{self.article_detail.category}',
    doi='{self.article_detail.doi}',
    author_corresponding='{self.article_detail.author_corresponding}',
    author_corresponding_institution='{self.article_detail.author_corresponding_institution}',
    version='{self.article_detail.version}',
    type='{self.article_detail.type}',
    license='{self.article_detail.license}',
    published='{self.article_detail.published}',
    server='{self.article_detail.server}')"""

    @classmethod
    def from_doi(cls, doi: str, server: str = "biorxiv", **kwargs):
        article_detail = get_content_detail_by_doi(doi, server=server)
        return cls(article_detail, **kwargs)

    @classmethod
    def from_content_page_url(cls, url: str, **kwargs):
        article_detail = get_content_detail_for_page(url)
        return cls(article_detail, **kwargs)

    def display_html(self):
        display(HTML(self.html))

    def get_overview(self, **kwargs):
        """
        It takes an Article object, extracts the images and metadata from it, generates an HTML file
        that displays the images and metadata, and opens the HTML file in a web browser
        """

        return OverviewHtml.from_article(self, **kwargs)


class OverviewHtml:
    def __init__(
        self, images: list, article_detail: ArticleDetail, save_images_to_tempfiles: bool = True
    ):
        self.images = images
        self.article_detail = article_detail
        self.save_images_to_tempfiles = save_images_to_tempfiles

        # Generate the HTML that will display the images
        html = '<html><body>'
        html += generate_metadata_html(article_detail)

        temp_files = []
        for image in images:
            output = generate_image_html(image, save_images_to_tempfiles=save_images_to_tempfiles)
            temp_file_name = output.get('temp_file_name')
            if temp_file_name:
                temp_files.append(temp_file_name)
            html += output.get('html')
        html += """
            </body>
        </html>
        """
        self.html = html
        self.temp_files = temp_files

    @classmethod
    def from_article(cls, article: Article, **kwargs):
        return cls(article.data['images'], article.article_detail, **kwargs)

    def display(self, cleanup: bool = True):
        # Create a temporary file to hold the HTML
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html') as f:
            # Write the HTML to the temporary file
            f.write(self.html)
            # Flush the file to ensure that it is written to disk
            f.flush()

            webbrowser.open(f.name)

        if cleanup:
            # wait one second
            time.sleep(1)

            # delete the temporary files
            for f in self.temp_files:
                os.remove(f)


def get_overview_html(
    images: list, article_detail: ArticleDetail, save_images_to_tempfiles: bool = True
):

    # Generate the HTML that will display the images
    html = '<html><body>'
    html += generate_metadata_html(article_detail)

    temp_files = []
    for image in images:
        output = generate_image_html(image, save_images_to_tempfiles=save_images_to_tempfiles)
        temp_file_name = output.get('temp_file_name')
        if temp_file_name:
            temp_files.append(temp_file_name)
        html += output.get('html')
    html += """
        </body>
    </html>
    """
    return html, temp_files


def generate_metadata_html(detail: ArticleDetail) -> str:
    """
    It takes an ArticleDetail object and returns a string of HTML

    Args:
        detail (ArticleDetail): ArticleDetail

    Returns:
        A string of HTML code.
    """
    metadata = f"""
    <style>
        .metadata {{
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 50%;
            margin: 0 auto;
        }}
        .metadata h1 {{
            font-size: 36px;
            margin-bottom: 20px;
        }}
        .metadata p {{
            font-size: 18px;
            margin: 10px 0;
        }}
        .metadata a {{
            text-decoration: none;
            color: blue;
        }}
        .metadata hr {{
            width: 75%;
            border: 0;
            height: 1px;
            background-color: #333;
            margin: 40px 0;
        }}
    </style>
    <div class="metadata">
        <h1>{detail.title}</h1>
        <p>Authors: {"; ".join(detail.authors)}</p>
        <p>Date: {detail.date}</p>
        <p>Category: {detail.category}</p>
        <p>DOI: <a href="https://doi.org/{detail.doi}">{detail.doi}</a></p>
        <p>Corresponding author: {detail.author_corresponding}</p>
        <p>Corresponding author institution: {detail.author_corresponding_institution}</p>
        <p>Version: {detail.version}</p>
        <p>Type: {detail.type}</p>
        <p>License: {detail.license}</p>
        <p>Abstract: {detail.abstract}</p>
        <p>PDF URL: <a href="{detail.pdf_url}">{detail.pdf_url}</a></p>
        <p>JATS XML: <a href="{detail.jatsxml}">{detail.jatsxml}</a></p>
        <hr>
    </div>
    """
    return metadata


def image_html_template(
    width,
    height,
    bytes_str: str = None,
    temp_file_name: str = None,
    caption: str = None,
    image_number: int = None,
) -> str:
    if bytes_str:
        src = f'data:image/jpeg;base64,{urllib.parse.quote(bytes_str)}'
    else:
        src = temp_file_name
    return f"""
    <table>
        <tr>
            <td>
                <p><font size="+2">Image {image_number}</font></p>
                <img src="{src}" width="{width}" height="{height}" style="max-width: 75%; height: auto;"/><br>
            </td>
            <td>
                <p>{caption}</p>
            </td>
        </tr>
    </table>
    """


def generate_image_html(image: Dict, save_images_to_tempfiles: bool) -> dict:
    """
    It takes an image dictionary and a boolean indicating whether to save the image to a file, and
    returns a dictionary containing the HTML string and the file name of the temporary file where
    the image is saved.

    Args:
        image (Dict): Dict
        save_images_to_tempfiles (bool): A boolean indicating whether to save the image to a file.

    Returns:
        A dictionary containing the HTML string and the file name of the temporary file.
    """
    # If the 'save_images' parameter is True, save the image to a temporary file
    width = image['image'].width
    height = image['image'].height
    caption = image.get('caption', '')
    image_number = image['image_number']
    if save_images_to_tempfiles:
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.jpg', delete=False) as f:
            image['image'].save(f, format='JPEG')
            # Flush the file to ensure that it is written to disk
            f.flush()
            # Use the temporary file's name as the 'src' attribute of an '<img>' element
            temp_file_name = f.name
        html = image_html_template(
            width, height, temp_file_name=temp_file_name, caption=caption, image_number=image_number
        )
    else:
        # Encode the image as a base64 string
        buffered = BytesIO()
        image['image'].save(buffered, format="JPEG")
        bytes_str = base64.b64encode(buffered.getvalue())
        temp_file_name = None
        html = image_html_template(
            width, height, bytes_str=bytes_str, caption=caption, image_number=image_number
        )

    return {'html': html, 'temp_file_name': temp_file_name}
