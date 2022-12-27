import modal

from paperview.modal_image import image
from paperview.retrieval.biorxiv_api import Article

stub = modal.Stub("paperview_overview_jobs")


@stub.function(image=image, retries=3, timeout=120)
def get_overview(doi: str = None, page: str = None):
    if doi:
        article = Article.from_doi(doi)
    else:
        article = Article.from_content_page_url(page)

    overview = article.get_overview(save_images_to_tempfiles=False)
    return overview.html
