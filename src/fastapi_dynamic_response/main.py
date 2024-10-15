from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles

from fastapi_dynamic_response import globals
from fastapi_dynamic_response.__about__ import __version__
from fastapi_dynamic_response.base.router import router as base_router
from fastapi_dynamic_response.dependencies import get_content_type
from fastapi_dynamic_response.middleware import (
    Sitemap,
    catch_exceptions_middleware,
    respond_based_on_content_type,
    set_prefers,
)
from fastapi_dynamic_response.zpages.router import router as zpages_router

app = FastAPI(
    title="FastAPI Dynamic Response",
    version=__version__,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    # openapi_tags=tags_metadata,
    # exception_handlers=exception_handlers,
    debug=True,
    dependencies=[
        Depends(set_prefers),
    ],
)
app.include_router(zpages_router)
app.include_router(base_router)
app.middleware("http")(Sitemap(app))
app.middleware("http")(catch_exceptions_middleware)
app.middleware("http")(respond_based_on_content_type)
app.mount("/static", StaticFiles(directory="static"), name="static")


# Flag to indicate if the application is ready


@app.on_event("startup")
async def startup_event():
    # Perform startup actions, e.g., database connections
    # If all startup actions are successful, set is_ready to True
    globals.is_ready = True
    globals.routes = [route.path for route in app.router.routes if route.path]


@app.get("/sitemap")
async def sitemap(
    request: Request,
    content_type: str = Depends(get_content_type),
):
    request.state.template_name = "sitemap.html"
    available_routes = [route.path for route in app.router.routes if route.path]
    return {"available_routes": available_routes}
