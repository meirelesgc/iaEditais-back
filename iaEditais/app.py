import os
from pathlib import Path

import tomli
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from iaEditais import workers
from iaEditais.core import broker
from iaEditais.core.settings import Settings
from iaEditais.routers import auth, stats, units, users
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

PROJECT_FILE = Path(__file__).parent.parent / 'pyproject.toml'

# Diretórios
BASE_DIR = os.path.dirname(__file__)
STORAGE_DIR = os.path.join(BASE_DIR, 'storage')
UPLOADS_DIR = os.path.join(STORAGE_DIR, 'uploads')
TEMP_DIR = os.path.join(STORAGE_DIR, 'temp')

for directory in [STORAGE_DIR, UPLOADS_DIR, TEMP_DIR]:
    os.makedirs(directory, exist_ok=True)


SETTINGS = Settings()

# Aplicação
app = FastAPI(docs_url='/swagger')

app.mount('/uploads', StaticFiles(directory=UPLOADS_DIR), name='uploads')

app.add_middleware(
    CORSMiddleware,
    allow_origins=SETTINGS.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


# Routers principais
app.include_router(units.router)
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(stats.router)

# Routers de documentação
app.include_router(docs.router)
app.include_router(kanban.router)
app.include_router(releases.router)
app.include_router(messages.router)
app.include_router(docs_ws.router)

# Routers de árvore
app.include_router(sources.router)
app.include_router(typifications.router)
app.include_router(taxonomies.router)
app.include_router(branches.router)

# Routers de evaluation
app.include_router(test_collections.router)
app.include_router(test_cases.router)
app.include_router(metrics.router)
app.include_router(models.router)
app.include_router(test_runs.router)
app.include_router(test_results.router)

# Eventos assincronos
app.include_router(workers.router)
app.include_router(broker.router)


@app.get('/info')
async def info():
    with PROJECT_FILE.open('rb') as f:
        data = tomli.load(f)
    project = data.get('project', {})
    urls = data.get('tool', {}).get('poetry', {}).get('urls', {})
    authors = project.get('authors', [])
    authors_str = [f'{a.get("name")} <{a.get("email")}>' for a in authors]
    return {
        'name': project.get('name'),
        'version': project.get('version'),
        'description': project.get('description'),
        'authors': authors_str,
        'license': project.get('license'),
        'urls': urls,
    }
