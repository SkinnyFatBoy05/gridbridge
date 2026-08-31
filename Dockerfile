FROM python:3.14.7-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_PROGRESS=1

WORKDIR /app
RUN pip install --no-cache-dir uv==0.8.18
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY config ./config
COPY dbt ./dbt
RUN uv sync --frozen --no-dev

ENTRYPOINT ["uv", "run", "gridbridge"]
CMD ["--help"]

