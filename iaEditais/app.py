import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from iaEditais.core import ws
from iaEditais.core.dependencies import Cache
from iaEditais.core.settings import Settings
from iaEditais.core.ws import manager
from iaEditais.events import events
from iaEditais.routers import auth, units, users
from iaEditais.routers.check_tree import (
    branches,
    sources,
    taxonomies,
    typifications,
)
from iaEditais.routers.docs import docs, kanban, messages, releases
from iaEditais.routers.evaluation import (
    metrics,
    test_case_metrics,
    test_cases,
    test_runs,
    tests,
)

# Diretórios
BASE_DIR = os.path.dirname(__file__)
STORAGE_DIR = os.path.join(BASE_DIR, 'storage')
UPLOADS_DIR = os.path.join(STORAGE_DIR, 'uploads')
TEMP_DIR = os.path.join(STORAGE_DIR, 'temp')

for directory in [STORAGE_DIR, UPLOADS_DIR, TEMP_DIR]:
    os.makedirs(directory, exist_ok=True)

# Aplicação
app = FastAPI(docs_url='/swagger')


# Routers principais
app.include_router(units.router)
app.include_router(users.router)
app.include_router(auth.router)

# Routers de documentação
app.include_router(docs.router)
app.include_router(kanban.router)
app.include_router(releases.router)
app.include_router(messages.router)

# Routers de árvore
app.include_router(sources.router)
app.include_router(typifications.router)
app.include_router(taxonomies.router)
app.include_router(branches.router)

# Routers de avaliação
app.include_router(tests.router)
app.include_router(metrics.router)
app.include_router(test_cases.router)
app.include_router(test_case_metrics.router)
app.include_router(test_runs.router)

# Routers de eventos
app.include_router(events.router)


@app.websocket('/ws/updates')
async def websocket_endpoint(websocket: WebSocket, cache: Cache):
    await manager.connect(websocket)
    try:
        while True:
            ws.cache_listener
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# print(Settings())
