import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from iaEditais.routers import units

BASE_DIR = os.path.dirname(__file__)
STORAGE_DIR = os.path.join(BASE_DIR, 'storage')
os.makedirs(STORAGE_DIR, exist_ok=True)

UPLOADS_DIR = os.path.join(STORAGE_DIR, 'uploads')
os.makedirs(UPLOADS_DIR, exist_ok=True)

TEMP_DIR = os.path.join(STORAGE_DIR, 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

app = FastAPI()

app.mount('/uploads', StaticFiles(directory=UPLOADS_DIR), name='uploads')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(units.router)


@app.get('/')
def root():
    return {'mensagem': 'API em funcionamento!'}
