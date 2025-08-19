from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from iaEditais.core.database import conn
from iaEditais.routers import auth, doc, statistics, unit, user
from iaEditais.routers.tree import branch, source, taxonomy, typification


@asynccontextmanager
async def lifespan(app: FastAPI):
    await conn.connect()
    yield
    await conn.disconnect()


app = FastAPI(
    title='IA Editais',
    docs_url='/swagger',
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(source.router, tags=['Source'])
app.include_router(taxonomy.router, tags=['Taxonomy'])
app.include_router(branch.router, tags=['Branch'])
app.include_router(doc.router, tags=['Doc'])
app.include_router(typification.router, tags=['Typification'])
app.include_router(user.router, tags=['User'])
app.include_router(unit.router, tags=['Unit'])
app.include_router(statistics.router)
app.include_router(auth.router)


@app.get('/')
def read_root():
    return {'message': 'Working'}
