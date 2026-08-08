FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked

COPY cocktail_assistant/ ./cocktail_assistant/
COPY data/ ./data/

# Pre-download the ONNX embedding model at build time
RUN python cocktail_assistant/download.py

EXPOSE 8501

CMD ["streamlit", "run", "cocktail_assistant/app.py", \
     "--server.port=8501", "--server.address=0.0.0.0"]
