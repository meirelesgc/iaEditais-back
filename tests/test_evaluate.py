from http import HTTPStatus
from datetime import datetime
from iaEditais.schemas.Evaluation import Evaluation


def test_create_evaluate(client, guideline_payload, evaluate_payload):
    response = client.post('/taxonomy/guideline/', json=guideline_payload)
    evaluate_payload['guideline_id'] = response.json()['id']

    response = client.post('/taxonomy/evaluate/', json=evaluate_payload)

    assert response.status_code == HTTPStatus.CREATED
    assert isinstance(Evaluation(**response.json()), Evaluation)
    assert isinstance(
        datetime.fromisoformat(response.json()['created_at']),
        datetime,
    )


def test_get_evaluate_with_one_record(
    client, guideline_payload, evaluate_payload
):
    response = client.post('/taxonomy/guideline/', json=guideline_payload)
    evaluate_payload['guideline_id'] = response.json()['id']
    response = client.post('/taxonomy/evaluate/', json=evaluate_payload)

    response = client.get('/taxonomy/evaluate/')

    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1


def test_get_evaluate_with_multiple_records(
    client, guideline_payload, evaluate_payload
):
    response = client.post('/taxonomy/guideline/', json=guideline_payload)
    evaluate_payload['guideline_id'] = response.json()['id']
    evaluates_payload = [evaluate_payload, evaluate_payload]

    for payload in evaluates_payload:
        client.post('/taxonomy/evaluate/', json=payload)

    response = client.get('/taxonomy/evaluate/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 2


def test_get_evaluate_with_filter(client, guideline_payload, evaluate_payload):
    for _ in range(2):
        response = client.post('/taxonomy/guideline/', json=guideline_payload)
        evaluate_payload['guideline_id'] = response.json()['id']
        client.post('/taxonomy/evaluate/', json=evaluate_payload)

    response = client.get(f'/taxonomy/evaluate/{response.json()["id"]}/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1


def test_update_evaluate(client, guideline_payload, evaluate_payload):
    response = client.post('/taxonomy/guideline/', json=guideline_payload)
    evaluate_payload['guideline_id'] = response.json()['id']
    response = client.post('/taxonomy/evaluate/', json=evaluate_payload)

    evaluate_payload = response.json()
    evaluate_payload['title'] = 'Updated Title'

    client.put('/taxonomy/evaluate/', json=evaluate_payload)
    response = client.get('/taxonomy/evaluate/')

    assert response.status_code == HTTPStatus.OK
    assert {'Updated Title'} == {g['title'] for g in response.json()}


def test_delete_evaluate(client, guideline_payload, evaluate_payload):
    response = client.post('/taxonomy/guideline/', json=guideline_payload)
    evaluate_payload['guideline_id'] = response.json()['id']
    response = client.post('/taxonomy/evaluate/', json=evaluate_payload)

    response = client.delete(f'/taxonomy/evaluate/{response.json()["id"]}')
    assert response.status_code == HTTPStatus.NO_CONTENT

    response = client.get('/taxonomy/evaluate/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []
