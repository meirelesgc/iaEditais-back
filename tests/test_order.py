from http import HTTPStatus
from iaEditais.schemas.doc import Doc, Release


def test_create_doc(client, typification):
    typification_id = str(typification.id)
    doc = {'name': 'Test Doc', 'typification': [typification_id]}
    response = client.post('/doc/', json=doc)
    assert response.status_code == HTTPStatus.CREATED
    assert isinstance(Doc(**response.json()), Doc)


def test_get_doc_with_one_doc(client, doc):
    response = client.get('/doc/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1


def test_get_doc_with_multiple_doc(client, create_doc):
    create_doc()
    create_doc()

    response = client.get('/doc/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 2


def test_delete_doc(client, doc):
    response = client.delete(f'/doc/{doc.id}/')
    assert response.status_code == HTTPStatus.NO_CONTENT

    response = client.get('/doc/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


def test_create_release(
    client, pdf, doc, create_taxonomy, create_branch, mocker
):
    for typification_id in doc.typification:
        response = create_taxonomy(typification_id=str(typification_id))
        create_branch(taxonomy_id=response.json()['id'])

    mocker.patch(
        'iaEditais.integrations.release_integration.analyze_release',
        side_effect=lambda release: release,
    )

    with open(pdf, 'rb') as buffer:
        file = {'file': ('testfile1.pdf', buffer, 'application/pdf')}
        response = client.post(f'/doc/{doc.id}/release/', files=file)

    assert response.status_code == HTTPStatus.CREATED
    assert isinstance(Release(**response.json()), Release)
