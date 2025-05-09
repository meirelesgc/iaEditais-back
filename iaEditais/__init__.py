from fastapi import FastAPI
from datetime import datetime
from iaEditais.config import Settings
from iaEditais.routers.branch_router import (
    router as branch_router,
)
from iaEditais.routers.doc_router import (
    router as doc_router,
)
from iaEditais.routers.source_router import router as source_router
from iaEditais.routers.taxonomy_router import (
    router as taxonomy_router,
)
from iaEditais.routers.typification_router import (
    router as typification_router,
)

app = FastAPI(
    root_path=Settings().ROOT_PATH,
    title='IA Editais',
)


@app.middleware('http')
async def log_requests(request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    process_time = datetime.now() - start_time
    print(
        f'Request {request.method} {request.url} - Tempo de execução: {process_time}'
    )
    return response


app.include_router(source_router, tags=['Source'])
app.include_router(taxonomy_router, tags=['Taxonomy'])
app.include_router(branch_router, tags=['Branch'])
app.include_router(doc_router, tags=['Doc'])
app.include_router(typification_router, tags=['Typification'])


@app.get('/')
def read_root():
    return {'message': 'Olá Mundo!'}
