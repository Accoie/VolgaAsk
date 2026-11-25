FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app/src PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /usr/local/bin/uv
RUN --mount=type=cache,target=/root/.cache/uv uv pip install --system torch torchvision --index-url https://download.pytorch.org/whl/cpu
COPY pyproject.toml .
RUN --mount=type=cache,target=/root/.cache/uv uv pip install --system -r pyproject.toml
COPY src ./src
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
