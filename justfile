set dotenv-load

default:
  @just --choose

setup: kind-create argo-install

teardown: kind-delete

kind-create:
    kind create cluster --name fastapi-dynamic-response

kind-delete:
    kind delete cluster --name fastapi-dynamic-response

argo-install:
    kubectl create namespace argocd
    kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
    kubectl get pods -n argocd
    kubectl apply -f argo

compile:
  uv pip compile pyproject.toml -o requirements.txt
venv:
  uv venv
build-podman:
  podman build -t docker.io/waylonwalker/fastapi-dynamic-response:0.0.2 .
run-podman:
  podman run -it --rm -p 8000:8000 --name fastapi-dynamic-response docker.io/waylonwalker/fastapi-dynamic-response:0.0.2
push-podman:
  podman push docker.io/waylonwalker/fastapi-dynamic-response:0.0.2
run:
  uv run -- uvicorn --reload --log-level debug src.fastapi_dynamic_response.main:app

run-workers:
  uv run -- uvicorn --workers 6 --log-level debug src.fastapi_dynamic_response.main:app

get-authorized:
  http GET :8000/example 'Authorization:Basic user1:password123'

get-admin:
  http GET :8000/example 'Authorization:Basic user2:securepassword'

get:
  http GET :8000/example

get-plain:
  http GET :8000/exa Content-Type:text/plain

get-rtf:
  http GET :8000/example Content-Type:application/rtf

get-json:
  http GET :8000/example Content-Type:application/json

get-html:
  http GET :8000/example Content-Type:text/html

get-md:
  http GET :8000/example Content-Type:application/markdown


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
