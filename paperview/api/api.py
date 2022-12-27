import fastapi
import modal
from fastapi.responses import HTMLResponse

from paperview.modal_image import image
from paperview.retrieval.biorxiv_api import (
    Article,
    ArticleDetail,
    get_content_detail_by_doi,
    get_content_detail_for_page,
)

web_app = fastapi.FastAPI()
stub = modal.Stub("paperview")

get_overview = modal.lookup("paperview_overview_jobs", "get_overview")


@web_app.get("/", response_class=HTMLResponse)
async def root():
    html_content = """
    <html>
        <head>
            <title>Paperview</title>
        </head>
        <body>
            <h1>Get a quick look at a bioRxiv manuscript</h1>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


@web_app.get("/metadata/", response_model=ArticleDetail)
async def get_content_detail(doi: str = None, page: str = None):
    if doi:
        return get_content_detail_by_doi(doi)
    else:
        return get_content_detail_for_page(page)


# @web_app.get("/overview/", response_class=HTMLResponse)
# async def get_overview(doi: str = None, page: str = None):
#     if doi:
#         article = Article.from_doi(doi)
#     else:
#         article = Article.from_content_page_url(page)

#     overview = article.get_overview(save_images_to_tempfiles=False)
#     return overview.html


@web_app.get("/parse/")
async def parse(doi: str = None, page: str = None):
    call = get_overview.spawn(doi=doi, page=page)
    return {"call_id": call.object_id}


@web_app.get("/overview_result/{call_id}", response_class=HTMLResponse)
async def poll_results(call_id: str):
    from modal.functions import FunctionCall

    function_call = FunctionCall.from_id(call_id)
    try:
        result = function_call.get()
    except TimeoutError:
        return fastapi.responses.JSONResponse(content="", status_code=202)

    return result


@stub.asgi(image=image)
def fastapi_app():
    return web_app


if __name__ == "__main__":
    stub.serve()
