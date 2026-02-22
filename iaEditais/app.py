import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from faststream.rabbit.fastapi import RabbitRouter
from redis.asyncio import Redis
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from iaEditais.core.cache import WebSocketManager
from iaEditais.core.settings import Settings
from iaEditais.routers import auth, stats, units, users
from iaEditais.routers.audit import audit_logs
from iaEditais.routers.check_tree import (
    branches,
    sources,
    taxonomies,
    typifications,
)
from iaEditais.routers.docs import docs, kanban, messages, releases
from iaEditais.routers.docs import ws as docs_ws
from iaEditais.routers.evaluation import (
    metrics,
    models,
    test_cases,
    test_collections,
    test_results,
    test_runs,
)
from iaEditais.workers import utils as w_utils
from iaEditais.workers.docs import releases as w_releases
from iaEditais.workers.evaluation import test_runs as w_test_runs

PROJECT_FILE = Path(__file__).parent.parent / 'pyproject.toml'


BASE_DIR = os.path.dirname(__file__)
STORAGE_DIR = os.path.join(BASE_DIR, 'storage')
UPLOADS_DIR = os.path.join(STORAGE_DIR, 'uploads')
TEMP_DIR = os.path.join(STORAGE_DIR, 'temp')

for directory in [STORAGE_DIR, UPLOADS_DIR, TEMP_DIR]:
    os.makedirs(directory, exist_ok=True)


SETTINGS = Settings()
BROKER_URL = SETTINGS.BROKER_URL

logging.basicConfig(
    level=SETTINGS.LOG_LEVEL, format='%(levelname)s: %(message)s'
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_instance = Redis.from_url(SETTINGS.CACHE_URL)
    socket_manager = WebSocketManager(client=redis_instance)
    app.state.redis = redis_instance
    app.state.socket_manager = socket_manager
    yield


app = FastAPI(
    docs_url='/swagger',
    lifespan=lifespan,
    root_path=SETTINGS.ROOT_PATH,
)

index = RabbitRouter(url=BROKER_URL)

app.mount('/uploads', StaticFiles(directory=UPLOADS_DIR), name='uploads')

app.add_middleware(
    ProxyHeadersMiddleware,
    trusted_hosts=SETTINGS.ALLOWED_ORIGINS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=SETTINGS.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


app.include_router(units.router)

app.include_router(stats.router)


app.include_router(docs.router)


app.include_router(messages.router)
app.include_router(docs_ws.router)


app.include_router(typifications.router)
app.include_router(taxonomies.router)
app.include_router(branches.router)

# Routers de evaluation (regulares)
app.include_router(test_collections.router)
app.include_router(test_cases.router)
app.include_router(metrics.router)
app.include_router(models.router)
app.include_router(test_results.router)

index.include_router(auth.router)
index.include_router(users.router)
index.include_router(w_releases.router)
index.include_router(w_utils.router)
index.include_router(releases.router)
index.include_router(kanban.router)
index.include_router(sources.router)
index.include_router(test_runs.router)
index.include_router(w_test_runs.router)

app.include_router(index)


app.include_router(audit_logs.router)
