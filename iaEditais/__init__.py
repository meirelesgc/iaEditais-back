from fastapi import FastAPI
from iaEditais.config import Settings
from iaEditais.routers.SourceRouter import router as source_router
from iaEditais.routers.Taxonomy.TaxonomyRouter import (
    router as taxonomy_router,
)
from iaEditais.routers.Taxonomy.BranchRouter import (
    router as branch_router,
)
from iaEditais.routers.OrderRouter import (
    router as order_router,
)
from iaEditais.routers.Taxonomy.TypificationRouter import (
    router as typification_router,
)

app = FastAPI(
    root_path=Settings().ROOT_PATH,
    title='IA Editais',
)

app.include_router(source_router, tags=['Source'])
app.include_router(taxonomy_router, tags=['Taxonomy'])
app.include_router(branch_router, tags=['Branch'])
app.include_router(order_router, tags=['Order'])
app.include_router(typification_router, tags=['Typification'])


@app.get('/')
def read_root():
    return {'message': 'Olá Mundo!'}
