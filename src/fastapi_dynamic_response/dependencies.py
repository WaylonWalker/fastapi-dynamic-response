from fastapi import Query


def get_content_type(
    content_type: str = Query(
        None, description="Specify the content type of the response"
    ),
):
    return content_type
