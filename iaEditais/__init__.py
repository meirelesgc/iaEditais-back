from fastapi import FastAPI
from iaEditais.config import Settings
from iaEditais.routers.SourceRouter import router

app = FastAPI(root_path=Settings().ROOT_PATH)

app.include_router(router, tags=['Source'])


@app.get('/')
def read_root():
    return {'message': 'Olá Mundo!'}
