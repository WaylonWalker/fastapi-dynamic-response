import typer
import uvicorn

from fastapi_dynamic_response.settings import settings


app_app = typer.Typer()


@app_app.callback()
def app():
    "model cli"


@app_app.command()
def run(
    env: str = typer.Option(
        "local",
        help="the environment to use",
    ),
):
    uvicorn.run(**settings.api_server.dict())


if __name__ == "__main__":
    app_app()
