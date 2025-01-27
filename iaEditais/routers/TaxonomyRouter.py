from fastapi import APIRouter

router = APIRouter()


@router.get('/taxonomy')
def get_taxonomy(): ...


@router.post('/taxonomy')
def create_taxonomy(): ...


@router.put('/taxonomy')
def update_taxonomy(): ...


@router.delete('/taxonomy')
def delete_taxonomy(): ...
