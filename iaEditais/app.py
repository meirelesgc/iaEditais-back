from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from iaEditais.config import Settings
from iaEditais.core.database import conn
from iaEditais.routers import doc, user
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
    allow_origins=[Settings().CLIENT],
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


@app.get('/')
def read_root():
    return {'message': 'Working'}
