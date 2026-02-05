"""
Rotas para execução de testes (TestRun).
"""

import json
from http import HTTPStatus
from typing import Annotated, Optional
from uuid import UUID, uuid4

from fastapi import Depends, File, Form, HTTPException, Query, UploadFile
from faststream.rabbit.fastapi import RabbitRouter as APIRouter

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.models import Branch, Document, DocumentHistory, Taxonomy, Typification
from iaEditais.repositories import evaluation_repository
from iaEditais.schemas import (
    FilterPage,
    SortBy,
    SortOrder,
    TestRunAccepted,
    TestRunExecute,
    TestRunList,
    TestRunPublic,
    TestRunStatus,
)
from iaEditais.services import storage_service

UPLOAD_DIRECTORY = 'iaEditais/storage/uploads'

router = APIRouter(
    prefix='/test-runs',
    tags=['avaliação, execução de testes'],
)


@router.get('/', response_model=TestRunList)
async def read_test_runs(
    session: Session,
    current_user: CurrentUser,
    filters: Annotated[FilterPage, Depends()],
    test_collection_id: Optional[UUID] = Query(
        None, description='ID da coleção de testes para filtrar (opcional)'
    ),
    test_case_id: Optional[UUID] = Query(
        None, description='ID do test case para filtrar os test runs (opcional)'
    ),
    status: Optional[str] = Query(
        None,
        description='Status do test run (PENDING, PROCESSING, EVALUATING, COMPLETED, ERROR)',
    ),
    sort_by: SortBy = Query(
        SortBy.CREATED_AT,
        description='Campo para ordenação (created_at ou updated_at)',
    ),
    sort_order: SortOrder = Query(
        SortOrder.DESC,
        description='Direção da ordenação (asc ou desc)',
    ),
):
    """Lista todos os test runs com filtros opcionais."""

    if status is not None:
        valid_statuses = [s.value for s in TestRunStatus]
        if status.upper() not in valid_statuses:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f'Invalid status. Must be one of: {", ".join(valid_statuses)}',
            )
        status = status.upper()

    if test_collection_id:
        test_collection = await evaluation_repository.get_test_collection(
            session, test_collection_id
        )
        if not test_collection or test_collection.deleted_at:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Test collection not found',
            )

    if test_case_id:
        test_case = await evaluation_repository.get_test_case(
            session, test_case_id
        )
        if not test_case or test_case.deleted_at:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Test case not found',
            )

    test_runs = await evaluation_repository.get_test_runs(
        session,
        test_collection_id=test_collection_id,
        test_case_id=test_case_id,
        status=status,
        offset=filters.offset,
        limit=filters.limit,
        sort_by=sort_by.value,
        sort_order=sort_order.value,
    )
    return {'test_runs': test_runs}


@router.get('/{test_run_id}', response_model=TestRunPublic)
async def read_test_run(
    test_run_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    """Busca um test run por ID."""
    test_run = await evaluation_repository.get_test_run(session, test_run_id)

    if not test_run or test_run.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Test run not found',
        )

    return test_run


@router.post(
    '/',
    status_code=HTTPStatus.ACCEPTED,
    response_model=TestRunAccepted,
)
async def execute_test_run(
    session: Session,
    current_user: CurrentUser,
    payload: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Inicia uma bateria de testes de forma assíncrona.
    Payload deve ser um JSON compatível com TestRunExecute.
    Retorna imediatamente com status 202 Accepted e o ID do test run.
    O processamento ocorre em background via worker.
    """
    print('DEBUG: Iniciando execução de test run - Checkpoint 1')
    try:
        print('DEBUG: Parseando payload JSON - Checkpoint 2')
        test_run_data_dict = json.loads(payload)

        # Validação via Pydantic
        try:
            print('DEBUG: Validando estrutura do payload - Checkpoint 3')
            test_run_execute = TestRunExecute(**test_run_data_dict)
        except Exception as e:
            raise ValueError(f'Invalid payload structure: {e}') from e

        if (
            not test_run_execute.test_collection_id
            and not test_run_execute.test_case_id
        ):
            raise ValueError(
                'Either test_collection_id or test_case_id is required'
            )

        # Salva arquivo para processamento posterior
        print('DEBUG: Salvando arquivo para processamento posterior - Checkpoint 4')
        file_path = await storage_service.save_file(file, UPLOAD_DIRECTORY)
        print(f'DEBUG: Arquivo salvo em: {file_path} - Checkpoint 4.1')

        # Busca test_case para obter test_collection_id e branch
        test_collection_id = test_run_execute.test_collection_id
        test_case = None
        if test_run_execute.test_case_id:
            print('DEBUG: Buscando test_case - Checkpoint 4.2')
            test_case = await evaluation_repository.get_test_case(
                session, test_run_execute.test_case_id
            )
            if test_case and not test_collection_id:
                test_collection_id = test_case.test_collection_id
                print(f'DEBUG: test_collection_id encontrado: {test_collection_id} - Checkpoint 4.3')

        # Busca tipificação a partir do branch do test_case
        print('DEBUG: Buscando tipificação do branch - Checkpoint 4.3.1')
        typification = None
        if test_case and test_case.branch_id:
            branch = await session.get(Branch, test_case.branch_id)
            if branch and branch.taxonomy_id:
                taxonomy = await session.get(Taxonomy, branch.taxonomy_id)
                if taxonomy and taxonomy.typification_id:
                    typification = await session.get(Typification, taxonomy.typification_id)
                    print(f'DEBUG: Tipificação encontrada: {typification.name} - Checkpoint 4.3.2')

        if not typification:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail='Test case branch must have an associated typification',
            )

        # Cria Document automaticamente com is_test=true
        print('DEBUG: Criando Document para teste - Checkpoint 4.4')
        filename = file.filename or 'documento'
        doc_uuid = uuid4()
        doc_name = f'Edital - {filename} - {str(doc_uuid)[:8]}'
        
        db_doc = Document(
            name=doc_name,
            description='Documento de teste criado automaticamente',
            identifier=str(doc_uuid),
            unit_id=current_user.unit_id,
            created_by=current_user.id,
            is_test=True,
        )
        session.add(db_doc)
        await session.flush()  # Para obter o ID antes de associar relacionamentos
        
        # Associa tipificação ao documento
        print('DEBUG: Associando tipificação ao documento - Checkpoint 4.4.1')
        db_doc.typifications = [typification]
        
        # Cria DocumentHistory
        print('DEBUG: Criando DocumentHistory - Checkpoint 4.4.2')
        history = DocumentHistory(
            document_id=db_doc.id,
            status='draft',
            created_by=current_user.id,
        )
        session.add(history)
        
        await session.commit()
        await session.refresh(db_doc)
        doc_id = db_doc.id
        print(f'DEBUG: Document criado com ID: {doc_id} - Checkpoint 4.5')

        # Cria test_run com status 'pending'
        print('DEBUG: Criando test_run com status pending - Checkpoint 5')
        test_run_data_db = {
            'test_collection_id': test_collection_id,
            'test_case_id': test_run_execute.test_case_id,
            'doc_id': doc_id,
            'status': TestRunStatus.PENDING.value,
        }
        test_run = await evaluation_repository.create_test_run(
            session, test_run_data_db, current_user
        )
        print(f'DEBUG: Test run criado com ID: {test_run.id} - Checkpoint 6')

        # Prepara dados para o worker
        worker_payload = {
            'test_run_id': str(test_run.id),
            'test_collection_id': str(test_collection_id) if test_collection_id else None,
            'test_case_id': (
                str(test_run_execute.test_case_id)
                if test_run_execute.test_case_id
                else None
            ),
            'metric_ids': [str(m) for m in test_run_execute.metric_ids],
            'model_id': (
                str(test_run_execute.model_id)
                if test_run_execute.model_id
                else None
            ),
            'doc_id': str(doc_id),
            'file_path': str(file_path),
            'created_by': str(current_user.id),
        }

        # Publica no RabbitMQ para processamento assíncrono
        print('DEBUG: Publicando no RabbitMQ para processamento - Checkpoint 7')
        await router.broker.publish(worker_payload, 'test_run_process')
        print('DEBUG: Mensagem publicada no RabbitMQ - Checkpoint 8')

        return TestRunAccepted(
            test_run_id=test_run.id,
            status=TestRunStatus.PENDING.value,
            message='Test run iniciado. Acompanhe o progresso via WebSocket.',
        )

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f'Invalid JSON in payload: {str(e)}',
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        print(f'DEBUG: Erro na execução: {str(e)} - Checkpoint ERROR')
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f'Internal server error: {str(e)}',
        ) from e

