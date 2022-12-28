from pathlib import Path

import fastapi
import fastapi.staticfiles
import modal
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from paperview.modal_image import image
from paperview.retrieval.biorxiv_api import (
    ArticleDetail,
    get_content_detail_by_doi,
    get_content_detail_for_page,
)

web_app = fastapi.FastAPI()
stub = modal.Stub("paperview")

get_overview = modal.lookup("paperview_overview_jobs", "get_overview")


@web_app.get("/metadata/", response_model=ArticleDetail)
async def get_content_detail(doi: str = None, page: str = None):
    if doi:
        return get_content_detail_by_doi(doi)
    else:
        return get_content_detail_for_page(page)


@web_app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <form action="/form-start-overview/" method="post">
        <input type="text" name="doi" placeholder="DOI" />
        <input type="text" name="url" placeholder="URL" />
        <input type="submit" />
    </form>
    """


class OverviewInput(BaseModel):
    doi: str = None
    url: str = None


@web_app.post("/start-overview/")
async def start_overview(overview_input: OverviewInput):
    doi = overview_input.doi
    url = overview_input.url
    # Call the get_overview function in the background, passing either the doi or url as an argument
    call = get_overview.spawn(doi=doi, page=url)

    # Return the call ID to the user
    return {"call_id": call.object_id}


@web_app.post("/form-start-overview/", response_class=HTMLResponse)
async def form_start_overview(request: fastapi.Request):
    form = await request.form()
    doi = form.get("doi")
    url = form.get("url")
    if doi:
        call = get_overview.spawn(doi=doi)
    elif url:
        call = get_overview.spawn(page=url)
    else:
        return fastapi.responses.JSONResponse(content="", status_code=400)
    # Return an HTML document with a hyperlink to the result URL
    result_url = f"/overview_result/{call.object_id}"
    html_content = f"""
    <html>
        <head>
            <title>Overview Result</title>
        </head>
        <body>
            <a href="{result_url}">Click here to view the overview result</a>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


# @web_app.post("/start-overview/")
# async def start_overview(request: OverviewInput):
#     doi = request.doi
#     url = request.url
#     if doi:
#         call = get_overview.spawn(doi=doi)
#     elif url:
#         call = get_overview.spawn(page=url)
#     else:
#         return fastapi.responses.JSONResponse(content="", status_code=400)
#     return {"call_id": call.object_id}


@web_app.get("/overview/")
async def request_overview(doi: str = None, page: str = None):
    return start_overview(OverviewInput(doi=doi, url=page))


@web_app.get("/overview_result/{call_id}", response_class=HTMLResponse)
async def poll_results(call_id: str):
    from modal.functions import FunctionCall

    function_call = FunctionCall.from_id(call_id)
    try:
        result = function_call.get()
    except TimeoutError:
        return fastapi.responses.JSONResponse(content="", status_code=202)

    return result


assets_path = Path(__file__).parent / "assets"


@stub.webhook(
    image=image,
    # mounts=[modal.Mount(remote_dir="/assets", local_dir=assets_path)]
)
def fastapi_app():
    # return web_app.mount("/", fastapi.staticfiles.StaticFiles(directory="/assets", html=True))
    return web_app


if __name__ == "__main__":
    stub.serve()
