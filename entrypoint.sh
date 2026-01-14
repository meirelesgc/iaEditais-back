#!/bin/sh

socat TCP-LISTEN:5672,fork TCP:iaeditais_rabbitmq:5672 &

alembic upgrade head

opentelemetry-instrument uvicorn --host 0.0.0.0 --port 8000 iaEditais.app:app --workers 4