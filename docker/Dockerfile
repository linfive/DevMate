FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONUTF8=1
WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONPATH="/app"

COPY docs ./docs
COPY src ./src
COPY tests ./tests
COPY checklist.md requirements.md README.md ./

CMD ["python", "-m", "src.devmate.main"]
