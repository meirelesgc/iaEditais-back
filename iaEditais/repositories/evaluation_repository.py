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
    Test,
    TestCase,
    TestCaseMetric,
    TestResult,
    TestRun,
    TestRunCase,
    User,
)

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


# ===========================
# Test Repository
# ===========================

async def create_test(session: Session, test_data: dict, current_user: CurrentUser):
    """Cria um novo teste."""
    db_test = Test(
        name=test_data['name'],
        description=test_data.get('description'),
        created_by=current_user.id,
    )
    session.add(db_test)
    await session.commit()
    await session.refresh(db_test)
    return db_test


async def get_test(session: Session, test_id: UUID):
    """Busca um teste por ID."""
    return await session.get(Test, test_id)


async def get_tests(session: Session, offset: int = 0, limit: int = 100):
    """Lista todos os testes ativos."""
    query = (
        select(Test)
        .where(Test.deleted_at.is_(None))
        .offset(offset)
        .limit(limit)
        .order_by(Test.created_at.desc())
    )
    result = await session.scalars(query)
    return result.all()


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
        model_id=metric_data.get('model_id'),
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
    # Resolve branch_id se branch_name foi fornecido
    branch_id = test_case_data.get('branch_id')
    if not branch_id and test_case_data.get('branch_name'):
        branch = await get_branch_by_name_or_id(session, branch_name=test_case_data['branch_name'])
        if branch:
            branch_id = branch.id
    
    db_test_case = TestCase(
        name=test_case_data['name'],
        test_id=test_case_data['test_id'],
        branch_id=branch_id,
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


async def get_test_cases(session: Session, test_id: Optional[UUID] = None, offset: int = 0, limit: int = 100):
    """Lista todos os casos de teste ativos."""
    query = select(TestCase).where(TestCase.deleted_at.is_(None))
    
    if test_id:
        query = query.where(TestCase.test_id == test_id)
    
    query = query.offset(offset).limit(limit).order_by(TestCase.created_at.desc())
    result = await session.scalars(query)
    return result.all()


# ===========================
# TestCaseMetric Repository
# ===========================

async def create_test_case_metric(session: Session, test_case_metric_data: dict, current_user: CurrentUser):
    """Cria uma nova associação entre caso de teste e métrica."""
    # Busca o test_case para obter o test_id
    test_case = await get_test_case(session, test_case_metric_data['test_case_id'])
    if not test_case:
        raise ValueError("Test case not found")
    
    db_test_case_metric = TestCaseMetric(
        test_case_id=test_case_metric_data['test_case_id'],
        metric_id=test_case_metric_data['metric_id'],
        test_id=test_case.test_id,
        created_by=current_user.id,
    )
    session.add(db_test_case_metric)
    await session.commit()
    await session.refresh(db_test_case_metric)
    return db_test_case_metric


async def get_test_case_metric(session: Session, test_case_metric_id: UUID):
    """Busca uma associação caso-métrica por ID."""
    return await session.get(TestCaseMetric, test_case_metric_id)


async def get_test_case_metrics(session: Session, test_case_id: Optional[UUID] = None, offset: int = 0, limit: int = 100):
    """Lista todas as associações caso-métrica ativas."""
    query = select(TestCaseMetric).where(TestCaseMetric.deleted_at.is_(None))
    
    if test_case_id:
        query = query.where(TestCaseMetric.test_case_id == test_case_id)
    
    query = query.offset(offset).limit(limit).order_by(TestCaseMetric.created_at.desc())
    result = await session.scalars(query)
    return result.all()


# ===========================
# TestRun Repository
# ===========================

async def create_test_run(session: Session, test_run_data: dict, current_user: CurrentUser):
    """Cria uma nova execução de teste."""
    db_test_run = TestRun(
        test_id=test_run_data['test_id'],
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
# TestRunCase Repository
# ===========================

async def create_test_run_cases(session: Session, test_run_id: UUID, case_metric_ids: list[UUID], test_id: UUID, current_user: CurrentUser):
    """Cria registros de casos executados em uma run."""
    test_run_cases = []
    
    for case_metric_id in case_metric_ids:
        db_test_run_case = TestRunCase(
            test_run_id=test_run_id,
            test_case_metric_id=case_metric_id,
            test_id=test_id,
            created_by=current_user.id,
        )
        session.add(db_test_run_case)
        test_run_cases.append(db_test_run_case)
    
    await session.commit()
    for trc in test_run_cases:
        await session.refresh(trc)
    
    return test_run_cases


async def get_test_run_cases(session: Session, test_run_id: UUID):
    """Busca todos os casos executados em uma run."""
    query = select(TestRunCase).where(
        TestRunCase.test_run_id == test_run_id,
        TestRunCase.deleted_at.is_(None)
    )
    result = await session.scalars(query)
    return result.all()


# ===========================
# TestResult Repository
# ===========================

async def create_test_result(session: Session, test_result_data: dict):
    """Cria um novo resultado de teste."""
    db_test_result = TestResult(
        test_run_case_id=test_result_data['test_run_case_id'],
        model_id=test_result_data.get('model_id'),
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
        # Join com test_run_cases para filtrar por test_run_id
        query = query.join(TestRunCase, TestResult.test_run_case_id == TestRunCase.id)
        query = query.where(TestRunCase.test_run_id == test_run_id)
    
    query = query.offset(offset).limit(limit).order_by(TestResult.created_at.desc())
    result = await session.scalars(query)
    return result.all()


# ===========================
# Document Repository
# ===========================

async def get_document(session: Session, doc_id: UUID):
    """Busca um documento por ID."""
    return await session.get(Document, doc_id)
