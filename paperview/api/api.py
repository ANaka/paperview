from pathlib import Path

import fastapi
import fastapi.staticfiles
import modal
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pyparsing import html_comment

from paperview.modal_image import image
from paperview.retrieval.biorxiv_api import (
    ArticleDetail,
    get_content_detail_by_doi,
    get_content_detail_for_page,
)

web_app = fastapi.FastAPI()
stub = modal.Stub("paperview_api", image=image)

get_overview = modal.lookup("paperview_overview_jobs", "get_overview")


# @web_app.get("/metadata/", response_model=ArticleDetail)
# async def get_content_detail(doi: str = None, page: str = None):
#     if doi:
#         return get_content_detail_by_doi(doi)
#     else:
#         return get_content_detail_for_page(page)


# class OverviewInput(BaseModel):
#     doi: str = None
#     url: str = None


# @web_app.post("/start-overview/")
# async def start_overview(overview_input: OverviewInput):
#     doi = overview_input.doi
#     url = overview_input.url
#     # Call the get_overview function in the background, passing either the doi or url as an argument
#     call = get_overview.spawn(doi=doi, page=url)

#     # Return the call ID to the user
#     return {"call_id": call.object_id}


@web_app.get("/", response_class=HTMLResponse)
async def root():
    html_content = f"""
    <html>
        <head>
            <title>Overview Result</title>
            <style>
                form {{
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }}
                input[type=text] {{
                    width: 50%;
                    padding: 12px 20px;
                    margin: 8px 0;
                    box-sizing: border-box;
                    border: 2px solid #ccc;
                    border-radius: 4px;
                }}
                input[type=submit] {{
                    width: 50%;
                    background-color: #4CAF50;
                    color: white;
                    padding: 14px 20px;
                    margin: 8px 0;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                }}
                input[type=submit]:hover {{
                    background-color: #45a049;
                }}
                p {{
                    text-align: center;
                    font-family: 'Open Sans', sans-serif;
                    font-size: 30px;
                    color: black;
                }}
                label {{
                    font-family: 'Open Sans', sans-serif;
                    font-size: 20px;
                    color: black;
                }}
            </style>
        </head>
        <body>
            <p>Enter a DOI or a URL from <a href="https://biorxiv.org">bioRxiv</a></p>
            <form method="post" action="/form-start-overview/">
                <label for="doi">DOI:</label><br>
                <input type="text" id="doi" name="doi"><br>
                <label for="url">URL:</label><br>
                <input type="text" id="url" name="url"><br><br>
                <input type="submit" value="Submit">
            </form>
            <br>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


def get_loading_screen(call_object_id):
    return f"""
    <html>
        <head>
            <title>Overview Result</title>
            <meta http-equiv="refresh" content="1;URL='/overview_result/{call_object_id}'" />
            <style>
                .loader {{
                    border: 16px solid #f3f3f3; /* Light grey */
                    border-top: 16px solid purple; /* Purple */
                    border-radius: 50%;
                    width: 120px;
                    height: 120px;
                    animation: spin 2s linear infinite;
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                }}

                @keyframes spin {{
                    0% {{
                        transform: rotate(0deg);
                    }}
                    100% {{
                        transform: rotate(360deg);
                    }}
                }}

                @keyframes pulse {{
                    0% {{
                        transform: scale(1);
                        opacity: 1;
                    }}
                    50% {{
                        transform: scale(1.1);
                        opacity: 0.5;
                    }}
                    100% {{
                        transform: scale(1);
                        opacity: 1;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="loader"></div>
        </body>
    </html>
    """


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

    # Redirect user to results when the job is complete
    html_content = get_loading_screen(call.object_id)

    return HTMLResponse(content=html_content, status_code=200)


# this is lazy, should refactor
@web_app.get("/request-overview/", response_class=HTMLResponse)
async def request_overview(doi: str = None, url: str = None):

    if doi:
        call = get_overview.spawn(doi=doi)
    elif url:
        call = get_overview.spawn(page=url)
    else:
        return fastapi.responses.JSONResponse(content="", status_code=400)

    # Redirect user to results when the job is complete
    html_content = get_loading_screen(call.object_id)

    return HTMLResponse(content=html_content, status_code=200)


@web_app.get("/overview_result_status/{call_id}")
async def overview_result_status(call_id: str):
    from modal.functions import FunctionCall

    function_call = FunctionCall.from_id(call_id)
    try:
        function_call.get(timeout=0)
        status = 'completed'
    except TimeoutError:
        status = 'pending'

    return {"status": status}


@web_app.get("/overview_result/{call_id}", response_class=HTMLResponse)
async def poll_results(call_id: str):
    from modal.functions import FunctionCall

    function_call = FunctionCall.from_id(call_id)
    result = function_call.get()
    if result is None:
        # Return a page with a JavaScript function that periodically checks the status
        # of the get_overview call and redirects the user to the results URL when the
        # call is complete
        html_content = f"""
        <html>
            <head>
                <title>Overview Result</title>
                <script>
                    function checkStatus() {{
                        var xhr = new XMLHttpRequest();
                        xhr.onreadystatechange = function() {{
                            if (this.readyState == 4 && this.status == 200) {{
                                var response = JSON.parse(this.responseText);
                                if (response.status == 'completed') {{
                                    window.location.href = '/overview_result/{call_id}';
                                }} else {{
                                    setTimeout(checkStatus, 1000);
                                }}
                            }}
                        }};
                        xhr.open("GET", '/overview_result_status/{call_id}', true);
                        xhr.send();
                    }}
                    setTimeout(checkStatus, 1000);
                </script>
            </head>
            <body>
                <p>Please wait while we retrieve the overview result...</p>
            </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=200)
    else:
        # Return the overview result
        return result


# assets_path = Path(__file__).parent / "assets"


@stub.asgi()
def fastapi_app():
    return web_app


if __name__ == "__main__":
    stub.serve()
