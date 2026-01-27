FROM python:3.13-slim AS builder

ENV POETRY_VIRTUALENVS_CREATE=false \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry

COPY poetry.lock pyproject.toml ./
RUN poetry install --no-interaction --no-ansi --without dev --no-root

RUN python -m spacy download pt_core_news_lg
RUN opentelemetry-bootstrap -a install


FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    socat libgl1 libxcb1 libglx0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local /usr/local

COPY . .
COPY entrypoint.sh .
RUN chmod +x ./entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
