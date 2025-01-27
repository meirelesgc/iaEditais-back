from fastapi import FastAPI
from iaEditais.config import Settings
from iaEditais.routers.SourceRouter import router as source_router
from iaEditais.routers.TaxonomyRouter import router as taxonomy_router

app = FastAPI(root_path=Settings().ROOT_PATH)

app.include_router(source_router, tags=['Source'])
app.include_router(taxonomy_router, tags=['Taxonomy'])


@app.get('/')
def read_root():
    return {'message': 'Olá Mundo!'}
