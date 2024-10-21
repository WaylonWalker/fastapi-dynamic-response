from fastapi import APIRouter, Depends, Request

from fastapi_dynamic_response.auth import admin, authenticated, has_scope
from fastapi_dynamic_response.base.schema import Message
from fastapi_dynamic_response.dependencies import get_content_type

router = APIRouter()


@router.get("/example")
async def get_example(
    request: Request,
    content_type: str = Depends(get_content_type),
):
    request.state.template_name = "example.html"
    return {"message": "Hello, this is an example", "data": [1, 2, 3, 4]}


@router.get("/private")
@authenticated
async def get_private(
    request: Request,
    content_type: str = Depends(get_content_type),
):
    request.state.template_name = "example.html"
    return {"message": "This page is private", "data": [1, 2, 3, 4]}


@router.get("/admin")
@admin
async def get_admin(
    request: Request,
    content_type: str = Depends(get_content_type),
):
    request.state.template_name = "example.html"
    return {"message": "This is only for admin users", "data": [1, 2, 3, 4]}


@router.get("/superuser")
@has_scope("superuser")
async def get_superuser(
    request: Request,
    content_type: str = Depends(get_content_type),
):
    request.state.template_name = "example.html"
    return {"message": "This is only for superusers", "data": [1, 2, 3, 4]}


@router.get("/error")
async def get_error(
    request: Request,
    content_type: str = Depends(get_content_type),
):
    request.state.template_name = "example.html"
    0 / 0
    return {"message": "Hello, this is an example", "data": [1, 2, 3, 4]}


@router.get("/another-example")
async def another_example(
    request: Request,
    content_type: str = Depends(get_content_type),
):
    request.state.template_name = "another_example.html"
    return {
        "title": "Another Example",
        "message": "Your cart",
        "items": ["apple", "banana", "cherry"],
    }


@router.get("/message")
async def message(
    request: Request,
    message_id: int,
    content_type: str = Depends(get_content_type),
):
    request.state.template_name = "post_message.html"
    return {"message": message.message}


@router.post("/message")
async def message(
    request: Request,
    message: Message,
    content_type: str = Depends(get_content_type),
):
    request.state.template_name = "post_message.html"
    return {"message": message.message}
