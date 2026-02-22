#!/bin/sh

alembic upgrade head

opentelemetry-instrument uvicorn iaEditais.app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --proxy-headers \
  --forwarded-allow-ips="127.0.0.1,10.0.0.1"
