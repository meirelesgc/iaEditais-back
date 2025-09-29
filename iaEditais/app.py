import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from iaEditais.routers import auth, units, users
from iaEditais.routers.check_tree import (
    branches,
    sources,
    taxonomies,
    typifications,
)
from iaEditais.routers.docs import docs, kanban, releases

# Diretórios
BASE_DIR = os.path.dirname(__file__)
STORAGE_DIR = os.path.join(BASE_DIR, 'storage')
UPLOADS_DIR = os.path.join(STORAGE_DIR, 'uploads')
TEMP_DIR = os.path.join(STORAGE_DIR, 'temp')

for directory in [STORAGE_DIR, UPLOADS_DIR, TEMP_DIR]:
    os.makedirs(directory, exist_ok=True)


# Aplicação
app = FastAPI(docs_url='/swagger')

app.mount('/uploads', StaticFiles(directory=UPLOADS_DIR), name='uploads')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


# Routers principais
app.include_router(units.router)
app.include_router(users.router)
app.include_router(auth.router)

# Routers de documentação
app.include_router(docs.router)
app.include_router(kanban.router)
app.include_router(releases.router)

# Routers de árvore
app.include_router(sources.router)
app.include_router(typifications.router)
app.include_router(taxonomies.router)
app.include_router(branches.router)
