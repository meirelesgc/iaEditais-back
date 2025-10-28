FROM python:3.13-slim AS builder

ENV POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

RUN pip install poetry

COPY poetry.lock pyproject.toml ./

RUN poetry install --no-interaction --no-ansi --without dev --no-root

FROM python:3.13-slim

ENV POETRY_VIRTUALENVS_CREATE=false \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y socat --no-install-recommends \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages

COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

COPY entrypoint.sh .
RUN chmod +x ./entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]