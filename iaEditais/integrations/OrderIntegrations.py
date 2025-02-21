from iaEditais.schemas.Order import Release, ReleaseFeedback
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import PromptTemplate
from iaEditais.integrations import get_model
from iaEditais.repositories import SourceRepository


def get_loader(path: str):
    return PyPDFLoader(path).load()


def analyze_release(release: Release) -> Release:
    model = get_model()

    loader = get_loader(f'storage/releases/{release.id}.pdf')
    rag = '\n\n---\n\n'.join(page.page_content for page in loader)

    TEMPLATE = """
        <Edital>
        {rag}
        </Edital>

        Você é um analista do serviço público brasileiro especializado na avaliação de critérios de editais.

        Neste momento, sua tarefa é verificar a relevância do seguinte critério:

        **Critério Principal:**  
        {taxonomy_title}  
        {taxonomy_description}  

        **Baseado na Fonte:**  
        {taxonomy_source}  

        Agora, analise o edital fornecido acima e responda:  

        O critério abaixo está contemplado no edital? Se sim, em qual parte?  

        **Critério Específico:**  
        {taxonomy_branch_title}  
        {taxonomy_branch_description}  

        {format_instructions}

        {query}
        """

    query = 'Justifique sua resposta com base no conteúdo do edital.'
    parser = JsonOutputParser(pydantic_object=ReleaseFeedback)
    prompt = PromptTemplate(
        template=TEMPLATE,
        input_variables=[
            'rag',
            'taxonomy_title',
            'taxonomy_description',
            'taxonomy_source',
            'taxonomy_branch_title',
            'taxonomy_branch_description',
            'format_instructions',
            'query',
        ],
        partial_variables={
            'format_instructions': parser.get_format_instructions()
        },
    )
    chain = prompt | model | parser

    for typification in release.taxonomy:
        for item in typification.get('taxonomy', []):
            source = [
                s['name']
                for s in SourceRepository.get_source()
                if s['id']
                in (item.get('source', []) + typification.get('source', []))
            ]
            for branch in item.get('branch', []):
                input_variables = {
                    'rag': rag,
                    'taxonomy_title': item.get('title'),
                    'taxonomy_description': item.get('description'),
                    'taxonomy_source': source,
                    'taxonomy_branch_title': branch.get('title'),
                    'taxonomy_branch_description': branch.get('description'),
                    'query': query,
                }
                branch['evaluate'] = chain.invoke(input_variables)
    return release
