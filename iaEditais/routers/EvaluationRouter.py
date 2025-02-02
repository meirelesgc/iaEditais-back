from fastapi import APIRouter

router = APIRouter()


@router.get('/eval/')
@router.get('/eval/{doc_id}/')
def get_evaluate():
    return {'message': 'Evaluation completed'}


@router.post('/eval/')
@router.post('/eval/{doc_id}/')
def post_evaluate():
    return {'message': 'Evaluation completed'}


@router.delete('/eval/{doc_id}')
def delete_evaluate():
    return {'message': 'Evaluation completed'}
