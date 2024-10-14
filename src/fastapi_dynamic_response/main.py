from fastapi import Depends, FastAPI, Request
from fastapi_dynamic_response import globals
from fastapi_dynamic_response.base.router import router as base_router
from fastapi_dynamic_response.dependencies import get_content_type
from fastapi_dynamic_response.middleware import (
    catch_exceptions_middleware,
    respond_based_on_content_type,
)
from fastapi_dynamic_response.zpages.router import router as zpages_router


app = FastAPI(debug=True)
app.include_router(zpages_router)
app.include_router(base_router)
app.middleware("http")(catch_exceptions_middleware)
app.middleware("http")(respond_based_on_content_type)


# Flag to indicate if the application is ready


@app.on_event("startup")
async def startup_event():
    # Perform startup actions, e.g., database connections
    # If all startup actions are successful, set is_ready to True
    globals.is_ready = True


@app.get("/sitemap")
async def sitemap(
    request: Request,
    content_type: str = Depends(get_content_type),
):
    request.state.template_name = "sitemap.html"
    available_routes = [route.path for route in app.router.routes if route.path]
    return {"available_routes": available_routes}
