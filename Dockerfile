FROM python:3.12-slim

ENV POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update && apt-get install -y libpq-dev supervisor

WORKDIR /app

COPY . .

RUN pip install poetry
RUN poetry config installer.max-workers 10
RUN poetry install --no-interaction --no-ansi

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 8000 8501

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
