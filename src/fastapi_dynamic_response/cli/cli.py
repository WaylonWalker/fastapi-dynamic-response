import typer

from fastapi_dynamic_response.cli.app import app_app

app = typer.Typer()

app.add_typer(app_app, name="app")
