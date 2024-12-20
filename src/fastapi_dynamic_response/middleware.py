from difflib import get_close_matches
from fastapi_dynamic_response.settings import settings
from io import BytesIO
import json
import time
import traceback
from typing import Any, Dict
from uuid import uuid4

from fastapi import Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
import html2text
from pydantic import BaseModel, model_validator
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

import base64
from fastapi_dynamic_response.constant import ACCEPT_TYPES
from fastapi_dynamic_response.globals import templates

import structlog

logger = structlog.get_logger()

console = Console()


class Prefers(BaseModel):
    JSON: bool = False
    html: bool = False
    rtf: bool = False
    text: bool = False
    markdown: bool = False
    partial: bool = False
    png: bool = False
    pdf: bool = False

    def __repr__(self):
        _repr = []
        for key, value in self.dict().items():
            if value:
                _repr.append(key + "=True")
        return f'Prefers({", ".join(_repr)})'

    @property
    def textlike(self) -> bool:
        return self.rtf or self.text or self.markdown

    @model_validator(mode="after")
    def check_one_true(self) -> Dict[str, Any]:
        format_flags = [
            self.JSON,
            self.html,
            self.rtf,
            self.text,
            self.markdown,
            self.png,
            self.pdf,
        ]
        if format_flags.count(True) != 1:
            message = "Exactly one of JSON, html, rtf, text, or markdown must be True."
            raise ValueError(message)
        return self


def log_request_state(request: Request):
    console.log(request.state.span_id)
    console.log(request.url.path)
    console.log(request.state.prefers)


async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    if str(response.status_code)[0] in "123":
        response.headers["X-Process-Time"] = str(process_time)
    return response


def set_bound_logger(request: Request, call_next):
    request.state.bound_logger = logger.bind()
    return call_next(request)


async def set_span_id(request: Request, call_next):
    span_id = uuid4()
    request.state.span_id = span_id
    request.state.bound_logger = logger.bind(span_id=request.state.span_id)

    response = await call_next(request)

    if str(response.status_code)[0] in "123":
        response.headers["x-request-id"] = str(span_id)
        response.headers["x-span-id"] = str(span_id)
    return response


def set_prefers(
    request: Request,
    call_next,
):
    content_type = (
        request.query_params.get(
            "content-type",
            request.query_params.get(
                "content_type",
                request.query_params.get("accept"),
            ),
        )
        or request.headers.get(
            "content-type",
            request.headers.get(
                "content_type",
                request.headers.get("accept"),
            ),
        )
    ).lower()
    if content_type == "*/*":
        content_type = None
    hx_request_header = request.headers.get("hx-request")
    user_agent = request.headers.get("user-agent", "").lower()
    referer = request.headers.get("referer", "")

    if content_type and "," in content_type:
        content_type = content_type.split(",")[0]

    request.state.bound_logger.info(
        "content_type set",
        content_type=content_type,
        hx_request_header=hx_request_header,
        user_agent=user_agent,
        referer=referer,
    )

    if content_type == "*/*":
        content_type = None
    if ("/docs" in referer or "/redoc" in referer) and content_type is None:
        content_type = "application/json"
    elif is_browser_request(user_agent) and content_type is None:
        request.state.bound_logger.info("browser agent request")
        content_type = "text/html"
    elif is_rtf_request(user_agent) and content_type is None:
        request.state.bound_logger.info("rtf agent request")
        content_type = "application/rtf"
    elif content_type is None:
        request.state.bound_logger.info("no content type request")
        content_type = content_type or "application/json"

    if hx_request_header == "true":
        content_type = "text/html-partial"
        # request.state.prefers = Prefers(html=True, partial=True)
        # content_type = "text/html"

    elif is_browser_request(user_agent) and content_type is None:
        content_type = "text/html"

    elif is_rtf_request(user_agent) and content_type is None:
        content_type = "text/rtf"

    # else:
    #     content_type = "application/json"

    partial = "partial" in content_type
    # if content_type in ACCEPT_TYPES:
    # for accept_type, accept_value in ACCEPT_TYPES.items():
    #     if accept_type in content_type:
    if content_type in ACCEPT_TYPES:
        request.state.prefers = Prefers(
            **{ACCEPT_TYPES[content_type]: True}, partial=partial
        )
    else:
        request.state.prefers = Prefers(JSON=True, partial=partial)

    request.state.content_type = content_type
    request.state.bound_logger = request.state.bound_logger.bind(
        # content_type=request.state.content_type,
        prefers=request.state.prefers,
    )
    return call_next(request)


class Sitemap:
    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next):
        request.state.routes = [
            route.path for route in self.app.router.routes if route.path
        ]
        return await call_next(request)


async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        print(traceback.format_exc())
        raise e


def is_browser_request(user_agent: str) -> bool:
    browser_keywords = [
        "mozilla",
        "chrome",
        "safari",
        "firefox",
        "edge",
        "wget",
        "opera",
    ]
    return any(keyword in user_agent.lower() for keyword in browser_keywords)


def is_rtf_request(user_agent: str) -> bool:
    rtf_keywords = ["curl", "httpie", "httpx"]
    return any(keyword in user_agent.lower() for keyword in rtf_keywords)


def get_screenshot(html_content: str) -> BytesIO:
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1280x1024")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get("data:text/html;charset=utf-8," + html_content)
    screenshot = driver.get_screenshot_as_png()
    driver.quit()
    buffer = BytesIO(screenshot)
    return buffer


def get_pdf(html_content: str, scale: float = 1.0) -> BytesIO:
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1280x1024")
    chrome_options.add_argument("--disable-dev-shm-usage")  # Helps avoid memory issues

    driver = webdriver.Chrome(options=chrome_options)
    driver.get("data:text/html;charset=utf-8," + html_content)

    # Generate PDF
    pdf = driver.execute_cdp_cmd(
        "Page.printToPDF",
        {
            "printBackground": True,  # Include CSS backgrounds in the PDF
            "paperWidth": 8.27,  # A4 paper size width in inches
            "paperHeight": 11.69,  # A4 paper size height in inches
            "marginTop": 0,
            "marginBottom": 0,
            "marginLeft": 0,
            "marginRight": 0,
            "scale": scale,
        },
    )["data"]

    driver.quit()

    # Convert base64 PDF to BytesIO
    pdf_buffer = BytesIO()
    pdf_buffer.write(base64.b64decode(pdf))
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


def format_json_as_plain_text(data: dict) -> str:
    """Convert JSON to human-readable plain text format with indentation and bullet points."""

    def _format_value(value, indent=2):
        if isinstance(value, dict):
            return format_json_as_plain_text(value)
        elif isinstance(value, list):
            return "\n".join([f"{' ' * indent}- {item}" for item in value])
        else:
            return str(value)

    output_lines = []
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            output_lines.append(f"{key}:\n{_format_value(value)}")
        else:
            output_lines.append(f"{key}: {value}")
    return "\n".join(output_lines)


def format_json_as_rich_text(data: dict, template_name: str) -> str:
    """Convert JSON to a human-readable rich text format using rich."""

    # pretty_data = Pretty(data, indent_guides=True)
    console = Console()

    template = templates.get_template(template_name)
    html_content = template.render(data=data)
    markdown_content = html2text.html2text(html_content)

    with console.capture() as capture:
        console.print(
            Panel(
                Markdown(markdown_content),
                title="Response Data",
                border_style="bold cyan",
            )
        )

    return capture.get()


def handle_not_found(request: Request, call_next, data: str):
    requested_path = request.url.path
    # available_routes = [route.path for route in app.router.routes if route.path]
    suggestions = get_close_matches(
        requested_path, request.state.routes, n=3, cutoff=0.5
    )

    request.state.template_name = "404.html"

    return templates.TemplateResponse(
        "404.html",
        {
            "request": request,
            "data": json.loads(data),
            "available_routes": request.state.routes,
            "requested_path": requested_path,
            "suggestions": suggestions,
        },
    )


async def respond_based_on_content_type(request: Request, call_next):
    requested_path = request.url.path
    if requested_path in ["/docs", "/redoc", "/openapi.json", "/static/app.css"]:
        request.state.bound_logger.info(
            "protected route returning non-dynamic response"
        )
        return await call_next(request)

    try:
        response = await call_next(request)

        if response.status_code == 404:
            request.state.bound_logger.info("404 not found")
            body = b"".join([chunk async for chunk in response.body_iterator])
            data = body.decode("utf-8")
            response = handle_not_found(
                request=request,
                call_next=call_next,
                data=data,
            )
        elif str(response.status_code)[0] not in "123":
            request.state.bound_logger.info(f"non-200 response {response.status_code}")
            # return await handle_response(request, response, data)
            return response
        else:
            body = b"".join([chunk async for chunk in response.body_iterator])
            data = body.decode("utf-8")

        return await handle_response(request, response, data)
    except Exception as e:
        request.state.bound_logger.info("internal server error")
        # print(traceback.format_exc())
        raise e
        if settings.ENV == "local":
            return HTMLResponse(
                content=f"Internal Server Error: {e!s} {traceback.format_exc()}",
                status_code=500,
            )
        else:
            return HTMLResponse(
                content=f"Internal Server Error: {e!s}", status_code=500
            )


async def handle_response(
    request: Request,
    response: Response,
    data: str,
):
    json_data = json.loads(data)

    template_name = getattr(request.state, "template_name", "default_template.html")
    if request.state.prefers.partial:
        request.state.bound_logger = logger.bind(template_name=template_name)
        template_name = "partial_" + template_name

    if request.state.prefers.JSON:
        request.state.bound_logger.info("returning JSON")
        return JSONResponse(
            content=json_data,
        )

    if request.state.prefers.html:
        request.state.bound_logger.info("returning html")
        return templates.TemplateResponse(
            template_name,
            {"request": request, "data": json_data},
        )

    if request.state.prefers.markdown:
        request.state.bound_logger.info("returning markdown")
        import html2text

        template = templates.get_template(template_name)
        html_content = template.render(data=json_data)
        markdown_content = html2text.html2text(html_content)
        return PlainTextResponse(content=markdown_content)

    if request.state.prefers.text:
        request.state.bound_logger.info("returning plain text")
        plain_text_content = format_json_as_plain_text(json_data)
        return PlainTextResponse(
            content=plain_text_content,
        )

    if request.state.prefers.rtf:
        request.state.bound_logger.info("returning rich text")
        rich_text_content = format_json_as_rich_text(json_data, template_name)
        return PlainTextResponse(
            content=rich_text_content,
        )

    if request.state.prefers.png:
        request.state.bound_logger.info("returning PNG")
        template = templates.get_template(template_name)
        html_content = template.render(data=json_data)
        screenshot = get_screenshot(html_content)
        return Response(
            content=screenshot.getvalue(),
            media_type="image/png",
        )

    if request.state.prefers.pdf:
        request.state.bound_logger.info("returning PDF")
        template = templates.get_template(template_name)
        html_content = template.render(data=json_data)
        scale = float(
            request.headers.get("scale", request.query_params.get("scale", 1.0))
        )
        console.log(f"Scale: {scale}")
        pdf = get_pdf(html_content, scale)

        return Response(
            content=pdf,
            media_type="application/pdf",
        )

    request.state.bound_logger.info("returning DEFAULT JSON")
    return JSONResponse(
        content=json_data,
    )


# Initialize the logger
async def log_requests(request: Request, call_next):
    # Log request details
    request.state.bound_logger = logger.bind(
        method=request.method, path=request.url.path
    )
    request.state.bound_logger.info(
        "Request received",
    )
    # logger.info(
    #     headers=dict(request.headers),
    #     prefers=request.state.prefers,
    # )

    # Process the request
    response = await call_next(request)

    # Log response details
    # logger.info(
    #     "Response sent",
    #     span_id=request.state.span_id,
    #     method=request.method,
    #     status_code=response.status_code,
    #     headers=dict(response.headers),
    # )

    return response
