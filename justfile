venv:
  uv venv
run:
  uv run -- uvicorn --reload --log-level debug src.fastapi_dynamic_response.main:app
