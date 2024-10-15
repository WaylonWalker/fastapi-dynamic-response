from difflib import get_close_matches
from io import BytesIO
import json
import traceback
from typing import Any, Dict
from uuid import uuid4

from fastapi import Request, Response
from fastapi.exceptions import (
    HTTPException as StarletteHTTPException,
    RequestValidationError,
)
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


def set_span_id(request: Request):
    span_id = uuid4()
    request.state.span_id = span_id


def set_prefers(
    request: Request,
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

    if hx_request_header == "true":
        request.state.prefers = Prefers(html=True, partial=True)
        return

    if is_browser_request(user_agent) and content_type is None:
        content_type = "text/html"

    elif is_rtf_request(user_agent) and content_type is None:
        content_type = "text/rtf"

    elif content_type is None:
        content_type = "application/json"

    # if content_type in ACCEPT_TYPES:
    for accept_type, accept_value in ACCEPT_TYPES.items():
        if accept_type in content_type:
            request.state.prefers = Prefers(**{accept_value: True})
            return
    request.state.prefers = Prefers(JSON=True, partial=False)


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


async def respond_based_on_content_type(
    request: Request,
    call_next,
    content_type: str,
    data: str,
):
    requested_path = request.url.path
    if requested_path in ["/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)

    return await call_next(request)


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
        return await call_next(request)

    try:
        response = await call_next(request)

        user_agent = request.headers.get("user-agent", "").lower()
        referer = request.headers.get("referer", "")
        content_type = request.query_params.get(
            "content_type",
            request.headers.get("content-type", request.headers.get("Accept")),
        )
        if "raw" in content_type:
            return await call_next(request)
        if content_type == "*/*":
            content_type = None
        if ("/docs" in referer or "/redoc" in referer) and content_type is None:
            content_type = "application/json"
        elif is_browser_request(user_agent) and content_type is None:
            content_type = "text/html"
        elif is_rtf_request(user_agent) and content_type is None:
            content_type = "application/rtf"
        elif content_type is None:
            content_type = content_type or "application/json"

        body = b"".join([chunk async for chunk in response.body_iterator])

        data = body.decode("utf-8")

        if response.status_code == 404:
            return handle_not_found(
                request=request,
                call_next=call_next,
                data=data,
            )
        if response.status_code == 422:
            return response
        if str(response.status_code)[0] not in "123":
            return response

        return await handle_response(request, data)
    # except TemplateNotFound:
    #     return HTMLResponse(content="Template Not Found ", status_code=404)
    except StarletteHTTPException as exc:
        return HTMLResponse(
            content=f"Error {exc.status_code}: {exc.detail}",
            status_code=exc.status_code,
        )
    except RequestValidationError as exc:
        return JSONResponse(status_code=422, content={"detail": exc.errors()})
    except Exception as e:
        print(traceback.format_exc())
        return HTMLResponse(content=f"Internal Server Error: {e!s}", status_code=500)


async def handle_response(request: Request, data: str):
    json_data = json.loads(data)

    template_name = getattr(request.state, "template_name", "default_template.html")
    if request.state.prefers.partial:
        template_name = "partial_" + template_name
    content_type = request.state.prefers

    if request.state.prefers.JSON:
        return JSONResponse(content=json_data)

    elif request.state.prefers.html:
        return templates.TemplateResponse(
            template_name, {"request": request, "data": json_data}
        )

    elif request.state.prefers.markdown:
        import html2text

        template = templates.get_template(template_name)
        html_content = template.render(data=json_data)
        markdown_content = html2text.html2text(html_content)
        return PlainTextResponse(content=markdown_content)

    elif request.state.prefers.text:
        plain_text_content = format_json_as_plain_text(json_data)
        return PlainTextResponse(content=plain_text_content)

    elif request.state.prefers.rtf:
        rich_text_content = format_json_as_rich_text(json_data, template_name)
        return PlainTextResponse(content=rich_text_content)

    elif request.state.prefers.png:
        template = templates.get_template(template_name)
        html_content = template.render(data=json_data)
        screenshot = get_screenshot(html_content)
        return Response(content=screenshot.getvalue(), media_type="image/png")

    elif request.state.prefers.pdf:
        template = templates.get_template(template_name)
        html_content = template.render(data=json_data)
        scale = float(
            request.headers.get("scale", request.query_params.get("scale", 1.0))
        )
        console.log(f"Scale: {scale}")
        pdf = get_pdf(html_content, scale)

        return Response(content=pdf, media_type="application/pdf")

    return JSONResponse(content=json_data)
