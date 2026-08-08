FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --locked --no-install-project

COPY cocktail_assistant/ ./cocktail_assistant/
RUN uv sync --locked
COPY data/ ./data/

# Pre-download the ONNX embedding model at build time
RUN python cocktail_assistant/download.py

EXPOSE 8501

COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
