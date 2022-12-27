import requests
from attrs import asdict
from bs4 import BeautifulSoup
from fastapi import FastAPI

from paperview.retrieval.biorxiv_api import (
    Article,
    ArticleDetail,
    get_content_detail_by_doi,
    get_content_detail_for_page,
)

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/metadata/", response_model=ArticleDetail)
async def get_content_detail(doi: str = None, page: str = None):
    if doi:
        return get_content_detail_by_doi(doi)
    else:
        return get_content_detail_for_page(page)
