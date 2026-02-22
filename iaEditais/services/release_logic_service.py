from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables.base import RunnableLambda

from iaEditais import prompts as PROMPTS
from iaEditais.core.dependencies import Model, VStore
from iaEditais.models import DocumentRelease, Typification
from iaEditais.schemas import DocumentReleaseFeedback
from iaEditais.schemas.typification import TypificationList

MAX_CHUNKS = 3
MARGIN_SIZE = 2

# --- Funções de Iteração e Filtros ---


def get_base_filter(db_release: DocumentRelease) -> dict:
    path = db_release.file_path.split('/')[-1]
    allowed_source = f'iaEditais/storage/uploads/{path}'
    return {'source': allowed_source}


def iter_typifications(eval_args: dict):
    for typification in eval_args.get('typifications') or []:
        yield typification


def iter_taxonomies(typification: dict):
    for taxonomy in typification.get('taxonomies') or []:
        yield taxonomy


def iter_branches(taxonomy: dict):
    for branch in taxonomy.get('branches') or []:
        yield branch


# --- Funções de Busca Vetorial ---


async def expand_branch_sessions(vstore: VStore, eval_args: dict):
    for typification in iter_typifications(eval_args):
        for taxonomy in iter_taxonomies(typification):
            for branch in iter_branches(taxonomy):
                original_chunks = branch.get('sessions', [])
                if not original_chunks:
                    continue

                docs_indices_map = {}
                for chunk in original_chunks:
                    source = chunk.metadata.get('source')
                    current_idx = chunk.metadata.get('chunk_index')
                    if source is None or current_idx is None:
                        continue
                    if source not in docs_indices_map:
                        docs_indices_map[source] = set()

                    start = max(0, current_idx - MARGIN_SIZE)
                    end = current_idx + MARGIN_SIZE + 1
                    for i in range(start, end):
                        docs_indices_map[source].add(i)

                expanded_chunks = []
                for source, indices_set in docs_indices_map.items():
                    indices_list = list(indices_set)
                    filter_dict = {
                        'source': source,
                        'chunk_index': {'$in': indices_list},
                    }
                    found_chunks = await vstore.asimilarity_search(
                        '', k=len(indices_list), filter=filter_dict
                    )
                    expanded_chunks.extend(found_chunks)

                if expanded_chunks:
                    expanded_chunks.sort(
                        key=lambda x: x.metadata.get('chunk_index', 0)
                    )
                    branch['sessions'] = expanded_chunks


async def get_branch_sessions(
    vstore: VStore,
    eval_args: dict,
    base_filter: dict,
    max_chunks: int = MAX_CHUNKS,
):
    for typification in iter_typifications(eval_args):
        for taxonomy in iter_taxonomies(typification):
            taxonomy_title = taxonomy.get('title')
            for branch in iter_branches(taxonomy):
                t_title = (taxonomy_title or '').strip()
                b_title = (branch.get('title') or '').strip()
                b_desc = (branch.get('description') or '').strip()
                query_text = f'{b_title}: {b_desc}'
                query = PROMPTS.QUERY.format(section=t_title, query=query_text)

                chunks = await vstore.asimilarity_search(
                    query, k=max_chunks, filter=base_filter
                )
                branch['sessions'] = chunks


async def get_eval_args(
    vstore: VStore, tree: list[Typification], db_release: DocumentRelease
):
    payload = {'typifications': tree}
    eval_args = TypificationList.model_validate(payload).model_dump(
        mode='json'
    )

    base_filter = get_base_filter(db_release)
    await get_branch_sessions(vstore, eval_args, base_filter)
    await expand_branch_sessions(vstore, eval_args)
    return eval_args


# --- Funções de LLM e Chain ---


def get_chain(model: Model):
    parser = JsonOutputParser(pydantic_object=DocumentReleaseFeedback)
    fmt = {'format_instructions': parser.get_format_instructions()}
    prompt = PromptTemplate(
        template=PROMPTS.DOCUMENT_ANALYSIS_PROMPT,
        input_variables=[
            'document',
            'source',
            'requirement',
            'expected_session',
            'query',
        ],
        partial_variables=fmt,
    )
    return prompt | model | parser


def _format_context(branch: dict) -> str:
    sessions = branch.get('sessions') or []
    sessions.sort(key=lambda x: x.metadata.get('chunk_index', 0))
    formatted_parts = []
    current_section = None
    for doc in sessions:
        section_title = doc.metadata.get('section_title', '').strip()
        content = getattr(
            doc, 'page_content', getattr(doc, 'content', str(doc))
        )
        header_pattern = f'SECTION: {section_title}\n\n'

        if content.startswith(header_pattern):
            clean_text = content[len(header_pattern) :]
        else:
            clean_text = content

        if section_title != current_section:
            if current_section is not None:
                formatted_parts.append('\n\n---\n\n')
            if section_title:
                formatted_parts.append(
                    f'## CONTEXTO DA SESSÃO: {section_title}\n'
                )
            current_section = section_title
        formatted_parts.append(clean_text)
    return ''.join(formatted_parts).strip()


def _create_eval_payload(taxonomy: dict, branch: dict) -> dict:
    expected_session = taxonomy.get('title', '').strip()
    req_title = branch.get('title', '').strip()
    req_desc = branch.get('description', '').strip()

    sources = taxonomy.get('sources') or []
    source_names = ', '.join([getattr(s, 'name', str(s)) for s in sources])

    # Presidio mapping recovery
    sessions = branch.get('sessions') or []
    full_mapping = {}
    for d in sessions:
        current_mapping = d.metadata.get('presidio_mapping') or {}
        for category, entities in current_mapping.items():
            if category not in full_mapping:
                full_mapping[category] = {}
            full_mapping[category].update(entities)

    return {
        'document': _format_context(branch),
        'source': source_names,
        'requirement': f'{req_title}: {req_desc}'
        if req_title and req_desc
        else (req_title or req_desc),
        'expected_session': expected_session,
        'query': f"Analise o item '{req_title}' na seção '{expected_session}'.",
        'presidio_mapping': full_mapping,
    }


async def simplify_eval_args(eval_args: dict) -> list[dict]:
    payloads = []
    for typification in iter_typifications(eval_args):
        for taxonomy in iter_taxonomies(typification):
            for branch in iter_branches(taxonomy):
                payload = _create_eval_payload(taxonomy, branch)
                if payload['document']:
                    payload['id'] = branch.get('id')
                    payloads.append(payload)
    return payloads


async def apply_tree(chain: RunnableLambda, eval_args: list[dict]):
    last_exception = None
    PROMPT = PROMPTS.DOCUMENT_ANALYSIS_PROMPT
    for _ in range(3):
        try:
            # LangChain batch execution
            response = await chain.abatch(eval_args)
            for item, result in zip(eval_args, response):
                # Guarda o prompt formatado para debug/log
                item['prompt'] = PROMPT.format(**item, format_instructions='')
                item.update(result)
            return eval_args
        except Exception as e:
            last_exception = e
    if last_exception:
        raise last_exception


def generate_description_prompt(eval_args: list[dict]) -> str:
    sorted_data = sorted(eval_args, key=lambda x: x['score'], reverse=True)
    top_results = sorted_data[:2]
    bottom_results = sorted_data[-2:]

    def format_items(items):
        text = ''
        for item in items:
            text += f'- Item: {item.get("query")}\n'
            text += f'  Nota: {item.get("score")}\n'
            text += f'  Status: {"Contemplado" if item.get("fulfilled") else "Não contemplado"}\n'
            text += f'  Feedback: {item.get("feedback")}\n\n'
        return text

    return PROMPTS.DESCRIPTION.format(
        top_text=format_items(top_results),
        bottom_text=format_items(bottom_results),
    ).strip()
