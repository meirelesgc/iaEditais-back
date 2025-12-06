#!/bin/sh

socat TCP-LISTEN:5672,fork TCP:iaeditais_rabbitmq:5672 &

alembic upgrade head

opentelemetry-instrument uvicorn --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="127.0.0.1,10.0.0.1" iaEditais.app:app