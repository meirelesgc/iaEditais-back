from fastapi import FastAPI
from iaEditais.config import Settings

app = FastAPI(root_path=Settings().ROOT_PATH)


@app.get('/')
def read_root():
    return {'message': 'Olá Mundo!'}
