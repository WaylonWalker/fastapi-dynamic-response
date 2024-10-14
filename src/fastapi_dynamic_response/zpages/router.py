from fastapi import APIRouter, HTTPException, Request
from fastapi_dynamic_response import globals

router = APIRouter()


@router.get("/livez")
async def livez(request: Request):
    """
    Liveness probe endpoint.
    Returns 200 OK if the application is alive.
    """
    request.state.template_name = "status.html"
    return {"status": "alive"}


@router.get("/readyz")
async def readyz(request: Request):
    """
    Readiness probe endpoint.
    Returns 200 OK if the application is ready to receive traffic.
    Returns 503 Service Unavailable if not ready.
    """
    request.state.template_name = "status.html"
    if globals.is_ready:
        return {"status": "ready"}
    else:
        raise HTTPException(status_code=503, detail="Not ready")


@router.get("/healthz")
async def healthz(request: Request):
    """
    Health check endpoint.
    Returns 200 OK if the application is healthy and ready.
    Returns 503 Service Unavailable if not healthy.
    """
    request.state.template_name = "status.html"
    if is_ready:
        return {"status": "healthy"}
    else:
        raise HTTPException(status_code=503, detail="Unhealthy")
