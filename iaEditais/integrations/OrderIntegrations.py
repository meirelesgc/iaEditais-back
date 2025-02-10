from iaEditais.schemas.Order import Release, ReleaseFeedback
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import PromptTemplate
from iaEditais.integrations import get_model


def get_loader(path: str):
    return PyPDFLoader(path).load()


def analyze_release(release: Release) -> list:
    model = get_model()

    taxonomy_score = []
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

    for taxonomy in release.taxonomy:
        score = {'id': taxonomy.get('id'), 'branches': []}
        for _, branch in enumerate(taxonomy.get('branches', [])):
            params = {
                'rag': rag,
                'taxonomy_title': taxonomy.get('title'),
                'taxonomy_description': taxonomy.get('description'),
                'taxonomy_source': taxonomy.get('source'),
                'taxonomy_branch_title': branch.get('title'),
                'taxonomy_branch_description': branch.get('description'),
                'query': query,
            }
            response = chain.invoke(params)
            response['id'] = branch.get('id')
            score['branches'].append(response)
        taxonomy_score.append(score)
    return taxonomy_score
