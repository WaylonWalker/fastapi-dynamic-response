from difflib import get_close_matches
from fastapi import Request, Response
from fastapi.exceptions import (
    HTTPException as StarletteHTTPException,
    RequestValidationError,
)
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
import html2text
from io import BytesIO
import json
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import traceback
from weasyprint import HTML as WeasyHTML

from fastapi_dynamic_response.globals import templates


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

    console = Console()
    # pretty_data = Pretty(data, indent_guides=True)

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


def handle_not_found(request: Request, data: str):
    requested_path = request.url.path
    available_routes = [route.path for route in app.router.routes if route.path]
    suggestions = get_close_matches(requested_path, available_routes, n=3, cutoff=0.5)

    return templates.TemplateResponse(
        "404.html",
        {
            "request": request,
            "data": json.loads(data),
            "available_routes": available_routes,
            "requested_path": requested_path,
            "suggestions": suggestions,
        },
    )


async def respond_based_on_content_type(request: Request, call_next):
    requested_path = request.url.path
    if requested_path in ["/docs", "/redoc", "/openapi.json"]:
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
            return handle_not_found(request, data)
        if response.status_code == 422:
            return response
        if str(response.status_code)[0] not in "123":
            return response

        return await handle_response(request, data, content_type)
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
        return HTMLResponse(content=f"Internal Server Error: {str(e)}", status_code=500)


async def handle_response(request: Request, data: str, content_type: str):
    json_data = json.loads(data)

    template_name = getattr(request.state, "template_name", "default_template.html")

    if content_type == "application/json":
        return JSONResponse(content=json_data)

    elif content_type == "text/html":
        return templates.TemplateResponse(
            template_name, {"request": request, "data": json_data}
        )

    elif content_type == "text/html-partial":
        return templates.TemplateResponse(
            template_name, {"request": request, "data": json_data}
        )

    elif (
        content_type == "text/markdown"
        or content_type == "md"
        or content_type == "markdown"
    ):
        import html2text

        template = templates.get_template(template_name)
        html_content = template.render(data=json_data)
        markdown_content = html2text.html2text(html_content)
        return PlainTextResponse(content=markdown_content)

    elif content_type == "text/plain":
        plain_text_content = format_json_as_plain_text(json_data)
        return PlainTextResponse(content=plain_text_content)

    elif (
        content_type == "text/rich"
        or content_type == "text/rtf"
        or content_type == "application/rtf"
    ):
        rich_text_content = format_json_as_rich_text(json_data, template_name)
        return PlainTextResponse(content=rich_text_content)

    elif content_type == "image/png":
        template = templates.get_template(template_name)
        html_content = template.render(data=json_data)
        screenshot = get_screenshot(html_content)
        return Response(content=screenshot.getvalue(), media_type="image/png")

    elif content_type == "application/pdf":
        template = templates.get_template(template_name)
        html_content = template.render(data=json_data)
        pdf = WeasyHTML(string=html_content).write_pdf()
        return Response(content=pdf, media_type="application/pdf")

    return JSONResponse(content=json_data)
