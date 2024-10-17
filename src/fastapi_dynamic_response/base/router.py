from fastapi import APIRouter, Depends, Request

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
