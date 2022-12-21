import os
import tempfile

import requests
from bs4 import BeautifulSoup

from paperview.retrieval.biorxiv_api import (
    ArticleDetail,
    get_all_content_details_by_interval,
    query_article_by_doi,
    query_content_detail_by_doi,
    query_content_detail_by_interval,
)


def get_content_detail_for_page(url: str) -> ArticleDetail:
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')

    doi_element = soup.find(class_='highwire-cite-metadata-doi highwire-cite-metadata')
    doi_url = doi_element.get_text()
    _doi = doi_url.split("https://doi.org/")[-1].strip()

    response = query_content_detail_by_doi(_doi)
    return ArticleDetail(**response.json()['collection'][0])


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
