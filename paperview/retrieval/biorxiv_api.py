import re
from typing import List

import requests
from attrs import define, field
from bs4 import BeautifulSoup
from IPython.core.display import HTML, display

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


def query_content_detail_by_doi(
    doi: str,
    server: str = "biorxiv",  # biorxiv or medRxiv
    format: str = "JSON",  # JSON or XML
) -> requests.models.Response:
    """https://api.biorxiv.org/details/[server]/[DOI]/na/[format] returns detail for a single manuscript.
    For instance, https://api.biorxiv.org/details/biorxiv/10.1101/339747 will output metadata for the biorxiv paper with DOI 10.1101/339747."""
    url = f"{BASE_URL}/details/{server}/{doi}/na/{format}"
    response = requests.get(url)
    return response


def validate_interval(interval: str) -> bool:
    """
    Checks if the interval is valid

    Args:
        interval (str): the interval to be checked

    Returns:
        bool: True if the interval is valid, False otherwise
    """
    # Check if the interval is a range of dates
    if re.match(r"\d{4}-\d{2}-\d{2}/\d{4}-\d{2}-\d{2}", interval):
        return True

    # Check if the interval is a numeric value for the N most recent posts
    if re.match(r"^\d+$", interval):
        return True

    # Check if the interval is a numeric value with the letter 'd' for the most recent N days of posts
    if re.match(r"^\d+d$", interval):
        return True

    return False


def validate_interval(interval: str) -> bool:
    # Check if the interval is a range of dates
    if re.match(r"\d{4}-\d{2}-\d{2}/\d{4}-\d{2}-\d{2}", interval):
        return True

    # Check if the interval is a numeric value for the N most recent posts
    if re.match(r"^\d+$", interval):
        return True

    # Check if the interval is a numeric value with the letter 'd' for the most recent N days of posts
    if re.match(r"^\d+d$", interval):
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

    response = query_content_detail_by_doi(_doi)
    return ArticleDetail(**response.json()['collection'][0])


class Article(object):
    def __init__(
        self,
        article_detail: ArticleDetail,
        extract_images: bool = True,
        extract_text: bool = True,
        extract_html: bool = True,
    ):
        self.article_detail = article_detail

        with pdf_extraction.NamedTemporaryPDF(self.article_detail.pdf_url) as f:
            if extract_images:
                self.images = pdf_extraction.extract_images(f)
            if extract_text:
                self.text = pdf_extraction.extract_text(f)
            if extract_html:
                self.html = pdf_extraction.extract_html(f)

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
        response = query_content_detail_by_doi(doi, server=server)
        article_detail = ArticleDetail(**response.json()["collection"])
        return cls(article_detail, **kwargs)

    @classmethod
    def from_content_page_url(cls, url: str, **kwargs):
        article_detail = get_content_detail_for_page(url)
        return cls(article_detail, **kwargs)

    def display_html(self):
        display(HTML(self.html))
