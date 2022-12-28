import diskcache as dc
import modal

from paperview.modal_image import image
from paperview.retrieval.biorxiv_api import Article, get_doi_from_page

stub = modal.Stub("paperview_overview_jobs")

volume = modal.SharedVolume().persist("cached_paperview_vol")


@stub.function(
    image=image, retries=3, timeout=3000, shared_volumes={"/root/cached_paperview_vol": volume}
)
def retrieve_article(doi: str = None, page: str = None):
    if page:
        doi = get_doi_from_page(page)

    # Check if the article is already in the cache
    article_cache = dc.Cache("/root/cached_paperview_vol/cached_articles")
    cached_article = article_cache.get(doi)
    if cached_article is not None:
        return cached_article
    else:
        article = Article.from_doi(doi)
        article_cache[doi] = article
        return article


@stub.function(
    image=image, retries=3, timeout=3000, shared_volumes={"/root/cached_paperview_vol": volume}
)
def get_overview(doi: str = None, page: str = None):
    if page:
        doi = get_doi_from_page(page)

    overview_cache = dc.Cache("/root/cached_paperview_vol/cached_overviews")
    cached_overview_html = overview_cache.get(doi)
    if cached_overview_html is not None:
        return cached_overview_html
    else:
        article = Article.from_doi(doi)
        overview = article.get_overview(save_images_to_tempfiles=False)
        overview_cache[doi] = overview.html
        return overview.html
