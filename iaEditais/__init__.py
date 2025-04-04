from fastapi import FastAPI
from iaEditais.config import Settings
from iaEditais.routers.source_router import router as source_router
from iaEditais.routers.Taxonomy.taxonomy_router import (
    router as taxonomy_router,
)
from iaEditais.routers.Taxonomy.branch_router import (
    router as branch_router,
)
from iaEditais.routers.doc_router import (
    router as doc_router,
)
from iaEditais.routers.Taxonomy.typification_router import (
    router as typification_router,
)

app = FastAPI(
    root_path=Settings().ROOT_PATH,
    title='IA Editais',
)

app.include_router(source_router, tags=['Source'])
app.include_router(taxonomy_router, tags=['Taxonomy'])
app.include_router(branch_router, tags=['Branch'])
app.include_router(doc_router, tags=['Doc'])
app.include_router(typification_router, tags=['Typification'])


@app.get('/')
def read_root():
    return {'message': 'Olá Mundo!'}
