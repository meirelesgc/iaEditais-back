FROM python:3.12-slim

ENV POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update && apt-get install -y libpq-dev

WORKDIR /app

COPY . .

RUN pip install poetry
RUN poetry config installer.max-workers 10
RUN poetry install --no-interaction --no-ansi

EXPOSE 8000
CMD ["poetry", "run", "uvicorn", "--host", "0.0.0.0", "iaEditais:app"]
