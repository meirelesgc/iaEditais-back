from contextlib import asynccontextmanager

from fastapi import FastAPI

from iaEditais.core.database import conn
from iaEditais.routers import doc
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


app.include_router(source.router, tags=['Source'])
app.include_router(taxonomy.router, tags=['Taxonomy'])
app.include_router(branch.router, tags=['Branch'])
app.include_router(doc.router, tags=['Doc'])
app.include_router(typification.router, tags=['Typification'])


@app.get('/')
def read_root():
    return {'message': 'Working'}
