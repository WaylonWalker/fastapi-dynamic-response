default:
  @just --choose

venv:
  uv venv

run:
  uv run -- uvicorn --reload --log-level debug src.fastapi_dynamic_response.main:app

get:
  http GET :8000/example

get-plain:
  http GET :8000/exa Content-Type=text/plain

get-rtf:
  http GET :8000/example Content-Type=application/rtf

get-json:
  http GET :8000 Content-Type=application/json

get-html:
  http GET :8000 Content-Type=text/html

get-md:
  http GET :8000 Content-Type=application/markdown


livez:
  http GET :8000/livez
healthz:
  http GET :8000/healthz
readyz:
  http GET :8000/readyz

# Install Tailwind CSS
install-tailwind:
    npm install tailwindcss

# Run Tailwind CLI to generate the CSS
build-tailwind:
    npx tailwindcss -i ./tailwind/input.css -o ./static/app.css --minify

# Watch for changes and rebuild CSS automatically
watch-tailwind:
    npx tailwindcss -i ./tailwind/input.css -o ./static/app.css --watch

# Remove node_modules (cleanup)
clean-node_modules:
    rm -rf node_modules

# Install dependencies and build CSS
setup-tailwind: install-tailwind build-tailwind
