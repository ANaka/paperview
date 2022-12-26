import datetime
import os
import re
import tempfile
import time
import webbrowser
from typing import Dict, List

import requests
from attrs import define, field
from bs4 import BeautifulSoup
from IPython.core.display import HTML
from IPython.display import display

from paperview.retrieval import pdf_extraction

BASE_URL = "https://api.biorxiv.org"


@define
class Message:
    status: str = field()
    interval: str = field(default=None)
    cursor: str = field(default=None)
    count: int = field(default=None)
    count_new_papers: int = field(default=None)
    total: int = field(default=None)

    def __repr__(self):
        return (
            f"Message(status='{self.status}', interval='{self.interval}', "
            f"cursor='{self.cursor}', count={self.count}, "
            f"count_new_papers={self.count_new_papers}, total={self.total})"
        )


def split_authors(authors: str) -> list:
    """Split a string of authors into a list of individual author names."""
    return authors.split("; ")


@define
class ArticleDetail:
    title: str = field()
    authors: list = field(converter=split_authors)
    date: str = field()
    category: str = field()
    doi: str = field()
    author_corresponding: str = field()
    author_corresponding_institution: str = field()
    version: str = field()
    type: str = field()
    license: str = field()
    abstract: str = field()
    published: str = field()
    server: str = field()
    jatsxml: str = field()

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
    return ArticleDetail(**response.json()["collection"][0])


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
    parsed_collections = [ArticleDetail(**collection) for collection in collections]

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


def get_content_detail_for_page(url: str) -> ArticleDetail:
    """
    It takes a URL, finds the DOI, and then queries the API for the article details

    Args:
        url (str): The URL of the article you want to get the metadata for.

    Returns:
        ArticleDetail
    """
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')

    doi_element = soup.find(class_='highwire-cite-metadata-doi highwire-cite-metadata')
    doi_url = doi_element.get_text()
    _doi = doi_url.split("https://doi.org/")[-1].strip()

    return get_content_detail_by_doi(_doi)


class Article(object):
    def __init__(
        self,
        article_detail: ArticleDetail,
        **kwargs,
    ):
        self.article_detail = article_detail

        with pdf_extraction.NamedTemporaryPDF(self.article_detail.pdf_url) as f:
            self.data = pdf_extraction.extract_all(f, **kwargs)

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

    def display_overview(self):
        """
        It takes an Article object, extracts the images and metadata from it, generates an HTML file
        that displays the images and metadata, and opens the HTML file in a web browser
        """

        def generate_metadata_html(detail: ArticleDetail) -> str:
            """
            It takes an ArticleDetail object and returns a string of HTML

            Args:
              detail (ArticleDetail): ArticleDetail

            Returns:
              A string of HTML code.
            """
            metadata = f"""
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
            """
            return metadata

        def generate_image_html(image: Dict, temp_file_name: str):
            """
            It takes an image dictionary and a temporary file name, and returns an HTML string that
            displays the image and its caption

            Args:
              image (Dict): Dict
              temp_file_name (str): The name of the temporary file that will be created to store the
            image.

            Returns:
              A function that takes two arguments, image and temp_file_name, and returns a string of
            html.
            """
            image_number = image['image_number']
            caption = image.get('caption', '')
            html = f"""
            <table>
                <tr>
                    <td>
                        <img src="{temp_file_name}" width="{image["image"].width}" height="{image["image"].height}" style="max-width: 100%; height: auto;"/><br>
                        <p>Figure {image_number}</p>
                    </td>
                    <td>
                        <p>{caption}</p>
                    </td>
                </tr>
            </table>
            """
            return html

        # Extract the list of image dictionaries from the 'data' attribute of the 'Article' instance
        images = self.data['images']
        detail = self.article_detail

        # Generate the HTML that will display the images
        html = '<html><body>'
        html += generate_metadata_html(detail)

        temp_files = []
        for image in images:
            # Save the image to a temporary file
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.jpg', delete=False) as f:
                image['image'].save(f, format='JPEG')
                # Flush the file to ensure that it is written to disk
                f.flush()
                # Use the temporary file's name as the 'src' attribute of an '<img>' element
                temp_files.append(f.name)
                html += generate_image_html(image=image, temp_file_name=f.name)
        html += """
            </body>
        </html>
        """

        # Create a temporary file to hold the HTML
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html') as f:
            # Write the HTML to the temporary file
            f.write(html)
            # Flush the file to ensure that it is written to disk
            f.flush()

            webbrowser.open(f.name)

        # wait one second
        time.sleep(1)

        # delete the temporary files
        for f in temp_files:
            os.remove(f)
