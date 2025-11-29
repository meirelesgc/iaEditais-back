from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.core.database import get_session
from iaEditais.core.security import get_current_user
from iaEditais.models import (
    AIModel,
    Branch,
    Document,
    Metric,
    TestCollection,
    TestCase,
    TestResult,
    TestRun,
    User,
)

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


# ===========================
# Test Collection Repository
# ===========================

async def create_test_collection(session: Session, test_collection_data: dict, current_user: CurrentUser):
    """Cria uma nova coleção de testes."""
    db_test_collection = TestCollection(
        name=test_collection_data['name'],
        description=test_collection_data.get('description'),
        created_by=current_user.id,
    )
    session.add(db_test_collection)
    await session.commit()
    await session.refresh(db_test_collection)
    return db_test_collection


async def get_test_collection(session: Session, test_collection_id: UUID):
    """Busca uma coleção de testes por ID."""
    return await session.get(TestCollection, test_collection_id)


async def get_test_collections(session: Session, offset: int = 0, limit: int = 100):
    """Lista todas as coleções de testes ativas."""
    query = (
        select(TestCollection)
        .where(TestCollection.deleted_at.is_(None))
        .offset(offset)
        .limit(limit)
        .order_by(TestCollection.created_at.desc())
    )
    result = await session.scalars(query)
    return result.all()


async def update_test_collection(session: Session, test_collection_id: UUID, test_collection_data: dict, current_user: CurrentUser):
    """Atualiza uma coleção de testes."""
    db_test_collection = await session.get(TestCollection, test_collection_id)
    if not db_test_collection:
        return None
    
    for key, value in test_collection_data.items():
        setattr(db_test_collection, key, value)
    
    db_test_collection.updated_by = current_user.id
    await session.commit()
    await session.refresh(db_test_collection)
    return db_test_collection


async def delete_test_collection(session: Session, test_collection_id: UUID, current_user: CurrentUser):
    """Remove (soft delete) uma coleção de testes."""
    db_test_collection = await session.get(TestCollection, test_collection_id)
    if not db_test_collection:
        return None
        
    from datetime import datetime
    db_test_collection.deleted_at = datetime.now()
    db_test_collection.deleted_by = current_user.id
    await session.commit()
    return db_test_collection


# ===========================
# AIModel Repository
# ===========================

async def create_ai_model(session: Session, model_data: dict, current_user: CurrentUser):
    """Cria um novo modelo de IA."""
    db_model = AIModel(
        name=model_data['name'],
        code_name=model_data['code_name'],
        created_by=current_user.id,
    )
    session.add(db_model)
    await session.commit()
    await session.refresh(db_model)
    return db_model


async def get_ai_model(session: Session, model_id: UUID):
    """Busca um modelo de IA por ID."""
    return await session.get(AIModel, model_id)


async def get_ai_models(session: Session, offset: int = 0, limit: int = 100):
    """Lista todos os modelos de IA ativos."""
    query = (
        select(AIModel)
        .where(AIModel.deleted_at.is_(None))
        .offset(offset)
        .limit(limit)
        .order_by(AIModel.created_at.desc())
    )
    result = await session.scalars(query)
    return result.all()


# ===========================
# Metric Repository
# ===========================

async def create_metric(session: Session, metric_data: dict, current_user: CurrentUser):
    """Cria uma nova métrica."""
    db_metric = Metric(
        name=metric_data['name'],
        criteria=metric_data.get('criteria'),
        evaluation_steps=metric_data.get('evaluation_steps'),
        threshold=metric_data.get('threshold', 0.5),
        created_by=current_user.id,
    )
    session.add(db_metric)
    await session.commit()
    await session.refresh(db_metric)
    return db_metric


async def get_metric(session: Session, metric_id: UUID):
    """Busca uma métrica por ID."""
    query = select(Metric).where(Metric.id == metric_id)
    return await session.scalar(query)


async def get_metrics(session: Session, offset: int = 0, limit: int = 100):
    """Lista todas as métricas ativas."""
    query = (
        select(Metric)
        .where(Metric.deleted_at.is_(None))
        .offset(offset)
        .limit(limit)
        .order_by(Metric.created_at.desc())
    )
    result = await session.scalars(query)
    return result.all()


async def update_metric(session: Session, metric_id: UUID, metric_data: dict, current_user: CurrentUser):
    """Atualiza uma métrica."""
    db_metric = await session.get(Metric, metric_id)
    if not db_metric:
        return None
    
    for key, value in metric_data.items():
        setattr(db_metric, key, value)
    
    db_metric.updated_by = current_user.id
    await session.commit()
    await session.refresh(db_metric)
    return db_metric


async def delete_metric(session: Session, metric_id: UUID, current_user: CurrentUser):
    """Remove (soft delete) uma métrica."""
    db_metric = await session.get(Metric, metric_id)
    if not db_metric:
        return None
        
    from datetime import datetime
    db_metric.deleted_at = datetime.now()
    db_metric.deleted_by = current_user.id
    await session.commit()
    return db_metric


# ===========================
# TestCase Repository
# ===========================

async def get_branch_by_name_or_id(session: Session, branch_id: Optional[UUID] = None, branch_name: Optional[str] = None):
    """Busca uma branch por ID ou nome."""
    if branch_id:
        return await session.get(Branch, branch_id)
    
    if branch_name:
        query = select(Branch).where(
            Branch.title == branch_name,
            Branch.deleted_at.is_(None)
        )
        result = await session.scalar(query)
        return result
    
    return None


async def create_test_case(session: Session, test_case_data: dict, current_user: CurrentUser):
    """Cria um novo caso de teste."""
    db_test_case = TestCase(
        name=test_case_data['name'],
        test_collection_id=test_case_data['test_collection_id'],
        branch_id=test_case_data.get('branch_id'),
        doc_id=test_case_data.get('doc_id'),
        input=test_case_data.get('input'),
        expected_feedback=test_case_data.get('expected_feedback'),
        expected_fulfilled=test_case_data.get('expected_fulfilled', False),
        created_by=current_user.id,
    )
    session.add(db_test_case)
    await session.commit()
    await session.refresh(db_test_case)
    return db_test_case


async def get_test_case(session: Session, test_case_id: UUID):
    """Busca um caso de teste por ID."""
    return await session.get(TestCase, test_case_id)


async def get_test_cases(session: Session, test_collection_id: Optional[UUID] = None, offset: int = 0, limit: int = 100):
    """Lista todos os casos de teste ativos."""
    query = select(TestCase).where(TestCase.deleted_at.is_(None))
    
    if test_collection_id:
        query = query.where(TestCase.test_collection_id == test_collection_id)
    
    query = query.offset(offset).limit(limit).order_by(TestCase.created_at.desc())
    result = await session.scalars(query)
    return result.all()


async def update_test_case(session: Session, test_case_id: UUID, test_case_data: dict, current_user: CurrentUser):
    """Atualiza um caso de teste."""
    db_test_case = await session.get(TestCase, test_case_id)
    if not db_test_case:
        return None
    
    for key, value in test_case_data.items():
        if value is not None:
            setattr(db_test_case, key, value)
    
    db_test_case.updated_by = current_user.id
    await session.commit()
    await session.refresh(db_test_case)
    return db_test_case


async def delete_test_case(session: Session, test_case_id: UUID, current_user: CurrentUser):
    """Remove (soft delete) um caso de teste."""
    db_test_case = await session.get(TestCase, test_case_id)
    if not db_test_case:
        return None
        
    from datetime import datetime
    db_test_case.deleted_at = datetime.now()
    db_test_case.deleted_by = current_user.id
    await session.commit()
    return db_test_case


# ===========================
# TestRun Repository
# ===========================

async def create_test_run(session: Session, test_run_data: dict, current_user: CurrentUser):
    """Cria uma nova execução de teste."""
    db_test_run = TestRun(
        test_collection_id=test_run_data.get('test_collection_id'),
        created_by=current_user.id,
    )
    session.add(db_test_run)
    await session.commit()
    await session.refresh(db_test_run)
    return db_test_run


async def get_test_run(session: Session, test_run_id: UUID):
    """Busca uma execução de teste por ID."""
    return await session.get(TestRun, test_run_id)


# ===========================
# TestResult Repository
# ===========================

async def create_test_result(session: Session, test_result_data: dict):
    """Cria um novo resultado de teste."""
    db_test_result = TestResult(
        test_run_id=test_result_data['test_run_id'],
        test_case_id=test_result_data['test_case_id'],
        metric_id=test_result_data['metric_id'],
        model_id=test_result_data['model_id'],
        threshold_used=test_result_data.get('threshold_used'),
        reason_feedback=test_result_data.get('reason_feedback'),
        score_feedback=test_result_data.get('score_feedback'),
        passed_feedback=test_result_data.get('passed_feedback'),
        actual_feedback=test_result_data.get('actual_feedback'),
        actual_fulfilled=test_result_data.get('actual_fulfilled'),
        passed_fulfilled=test_result_data.get('passed_fulfilled'),
        created_by=test_result_data.get('created_by'),
    )
    session.add(db_test_result)
    await session.flush()  # Gera o ID sem fazer commit completo
    result_id = db_test_result.id  # Extrai ID imediatamente
    await session.commit()
    
    return result_id  # Retorna apenas o UUID


async def get_test_result(session: Session, test_result_id: UUID):
    """Busca um resultado de teste por ID."""
    return await session.get(TestResult, test_result_id)


async def get_test_results(session: Session, test_run_id: Optional[UUID] = None, offset: int = 0, limit: int = 100):
    """Lista todos os resultados de teste."""
    query = select(TestResult).where(TestResult.deleted_at.is_(None))
    
    if test_run_id:
        query = query.where(TestResult.test_run_id == test_run_id)
    
    query = query.offset(offset).limit(limit).order_by(TestResult.created_at.desc())
    result = await session.scalars(query)
    return result.all()


# ===========================
# Document Repository
# ===========================

async def get_document(session: Session, doc_id: UUID):
    """Busca um documento por ID."""
    return await session.get(Document, doc_id)
