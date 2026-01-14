FROM python:3.13-slim

ENV POETRY_VIRTUALENVS_CREATE=false \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

RUN apt-get update && apt-get install -y socat --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

RUN pip install poetry

COPY poetry.lock pyproject.toml ./

RUN poetry install --no-interaction --no-ansi --without dev --no-root
RUN opentelemetry-bootstrap -a install

COPY . .
COPY entrypoint.sh .

RUN chmod +x ./entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
