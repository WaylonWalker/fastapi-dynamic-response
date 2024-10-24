from python:3.13
WORKDIR /app
COPY src src
COPY pyproject.toml .
COPY uv.lock .
COPY README.md .
COPY requirements.txt .

ENV VIRTUAL_ENV=/app/.venv
ENV PATH=${VIRTUAL_ENV}/bin:${PATH}

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

ENV HOME=/home/appuser
ENV PATH=${HOME}/.local/bin:${PATH}

RUN pip install --upgrade pip && \
 pip install uv && \
 uv venv
RUN uv pip install -r requirements.txt
RUN uv pip install .

COPY static static
COPY templates templates

EXPOSE 8000

ENTRYPOINT ["uvicorn"]
CMD ["src.fastapi_dynamic_response.main:app", "--host", "0.0.0.0", "--port", "8000"]
