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
