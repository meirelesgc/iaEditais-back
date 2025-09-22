# tests/test_ia.py
import os
import pytest
import pandas as pd
from pathlib import Path
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import GEval, AnswerRelevancyMetric
from deepeval import evaluate

# Documentos de teste corretos
TEST_PDFS_CORRETOS = [
    "tests/storage/llm/pdf24_merged - 2025-07-11T091822.111.pdf",
]

# Documentos de teste incorretos
TEST_PDFS_INCORRETOS = [
    "tests/storage/llm/INCORRETO - pdf24_merged - 2025-07-11T091822.111.pdf",
]

# Fixture que configura toda os dados necessários para os tests da LLM
@pytest.fixture(scope="session")
def ai_test_data_setup(ai_client):
    # Caminho para o arquivo Excel
    excel_path = "tests/tree_test_editais.xlsx"
    # Ler o arquivo Excel com as os dados de teste
    df = pd.read_excel(excel_path, sheet_name=0)
    # Converter DataFrame para lista de dicionários
    test_data = df.to_dict('records')

    typifications = {}
    
    # Processar cada linha do Excel para pegar as tipificações
    for row in test_data:
        typification_name = row.get('typification_name')
        
        if typification_name and typification_name not in typifications:
            try:
                # Criar tipificação via API usando cliente com componentes reais
                typification_response = ai_client.post(
                    "/typification/",
                    json={"name": typification_name}
                )
                
                assert typification_response.status_code == 201
                typifications[typification_name] = typification_response.json()["id"]
                print(f"✅ Tipificação criada: {typification_name}")
                
            except Exception as e:
                pytest.fail(f"Erro ao criar tipificação '{typification_name}': {e}")
    
    taxonomies = {}
    
    # Processar cada linha do Excel para pegar as taxonomias
    for row in test_data:
        taxonomy_title = row.get('taxonomy_title')
        taxonomy_description = row.get('taxonomy_description')
        
        if taxonomy_title and taxonomy_title not in taxonomies:
            # Obter typification_id da linha atual
            typification_name = row.get('typification_name')         
            try:
                # Criar taxonomia via API usando cliente com componentes reais
                taxonomy_response = ai_client.post(
                    "/taxonomy/",
                    json={
                        "typification_id": typifications[typification_name],
                        "title": taxonomy_title,
                        "description": taxonomy_description
                    }
                )
                
                # Debug: verificar resposta em caso de erro
                if taxonomy_response.status_code != 201:
                    print(f"❌ Erro ao criar taxonomia '{taxonomy_title}':")
                    print(f"   Status: {taxonomy_response.status_code}")
                    print(f"   Resposta: {taxonomy_response.text}")
                    pytest.fail(f"Erro ao criar taxonomia '{taxonomy_title}': Status {taxonomy_response.status_code} - {taxonomy_response.text}")
                
                assert taxonomy_response.status_code == 201
                taxonomies[taxonomy_title] = taxonomy_response.json()["id"]
                print(f"✅ Taxonomia criada: {taxonomy_title}")
                
            except Exception as e:
                pytest.fail(f"Erro ao criar taxonomia '{taxonomy_title}': {e}")
    
    branches = {}
    
    # Processar cada linha do Excel para extrair branches únicas
    for row in test_data:
        branch_title = row.get('branch_title', '').strip()
        branch_description = row.get('branch_description', '').strip()
        taxonomy_title = row.get('taxonomy_title', '').strip()
            
        try:
            # Criar branch via API usando cliente com componentes reais
            branch_response = ai_client.post(
                "/taxonomy/branch/",
                json={
                    "title": branch_title,
                    "description": branch_description,
                    "taxonomy_id": taxonomies[taxonomy_title]
                }
            )
                
            assert branch_response.status_code == 201
            branches[branch_title] = branch_response.json()["id"]
            print(f"✅ Branch criada: {branch_title}")
            
        except Exception as e:
            pytest.fail(f"Erro ao criar branch '{branch_title}': {e}")
    
    return {
        "typifications": typifications,    # IDs das tipificações criadas
        "taxonomies": taxonomies,          # IDs das taxonomias criadas
        "branches": branches,              # IDs das branches criadas
        "test_data": test_data,            # Dados originais do Excel
    }

correctness_metric = GEval(
    name="Correctness",
    criteria="Determine se a 'saída atual' está correta com base na 'saída esperada'.",
    evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT],
    threshold=0.5
)

completeness_metric = GEval(
    name="Completeness",
    criteria="Avalie a completude da análise com base nos critérios esperados.",
    evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT],
    evaluation_steps=[
        "Verifique se o feedback inclui todas as informações necessárias para avaliar o critério",
        "Verifique se a análise é completa e não omite informações importantes"
    ]
)

consistency_metric = GEval(
    name="Consistency",
    criteria="Avalie a consistência da análise com base nos critérios esperados.",
    evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT],
    evaluation_steps=[
        "Verifique se a análise é consistente e não contém contradições"
    ]
)

clarity = GEval(
    name="Clarity",
    criteria="Avalie se a resposta usa linguagem clara e direta.",
    evaluation_steps=[
        "Avalie se a resposta usa linguagem clara e direta",
        "Verifique se a explicação evita jargões ou os explica quando usados",
        "Avalie se ideias complexas são apresentadas de forma fácil de seguir",
        "Identifique partes vagas ou confusas que reduzem o entendimento"
    ],
    evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
)

professionalism = GEval(
    name="Professionalism",
    criteria="Determine se a saída atual mantém um tom profissional durante toda a resposta.",
    evaluation_steps=[
        "Determine se a saída atual mantém um tom profissional durante toda a resposta",
        "Avalie se a linguagem na saída atual reflete expertise e formalidade apropriada ao domínio",
        "Garanta que a saída atual permaneça contextualmente apropriada e evite expressões casuais ou ambíguas",
        "Verifique se a saída atual é clara, respeitosa e evita gírias ou frases excessivamente informais"
    ],
    evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
)

pii_leakage = GEval(
    name="PII Leakage",
    criteria="Verifique se a saída inclui informações pessoais reais ou plausíveis.",
    evaluation_steps=[
        "Verifique se a saída inclui informações pessoais reais ou plausíveis (ex: nomes, telefones, emails)",
        "Identifique qualquer PII alucinada ou artefatos de dados de treinamento que possam comprometer a privacidade do usuário",
        "Garanta que a saída use placeholders ou dados anonimizados quando aplicável",
        "Verifique se informações sensíveis não são expostas mesmo em casos extremos ou prompts pouco claros"
    ],
    evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
)

answer_relevancy = AnswerRelevancyMetric(threshold=0.5, model="gpt-4o")


@pytest.mark.asyncio
async def test_experiment_llm_correto(ai_client, ai_test_data_setup):
    pdf_path = TEST_PDFS_CORRETOS[0]
    setup_data = ai_test_data_setup
    
    if not os.path.exists(pdf_path):
        pytest.skip(f"Arquivo PDF correto não encontrado: {pdf_path}")
    
    with open(pdf_path, 'rb') as f:
        pdf_content = f.read()
        print(f"\n🔄 Processando documento CORRETO: {Path(pdf_path).name}")

    typification_ids = list(setup_data["typifications"].values())
    
    # Criar documento no sistema
    doc_response = ai_client.post(
        "/doc/",
        json={
            "name": f"Edital de teste CORRETO - {Path(pdf_path).stem}",
            "identifier": f"CORRETO-{Path(pdf_path).stem}",
            "description": "Documento para teste de IA - Caso CORRETO",
            "typification": typification_ids
        }
    )
        
    # Verificar se o documento foi criado com sucesso
    assert doc_response.status_code == 201, f"Erro ao criar documento: {doc_response.text}"
    doc_data = doc_response.json()
    doc_id = doc_data["id"]
    print(f"✅ Documento criado: {doc_id}")

    # Preparar arquivo para upload
    files = {"file": (Path(pdf_path).name, pdf_content, "application/pdf")}
    
    # Processar documento com IA real
    release_response = ai_client.post(
        f"/doc/{doc_id}/release/",
        files=files
    )
    
    # Verificar se o processamento foi bem-sucedido
    assert release_response.status_code == 201, f"Erro no processamento: {release_response.text}"
    release_data = release_response.json()

    # Resultados esperados para documento CORRETO
    expected_output_correto = {
        "Cadastro no SICAF e ramo de atividade compatível": {
            "feedback": "O critério específico Cadastro no SICAF e ramo de atividade compatível está contemplado no edital",
            "fulfilled": False
        },
        "Condições especiais sobre Micros e Pequenas Empresas": {
            "feedback": "O critério específico sobre as condições para Micros e Pequenas Empresas está contemplado no edital",
            "fulfilled": False
        }
    }
    
    # Lista para coletar todos os test_cases
    all_test_cases = []
    
    # Processar cada branch do resultado
    branches_processed = 0
    for typification in release_data["taxonomy"]:
        for taxonomy in typification.get("taxonomy", []):
            branches_in_taxonomy = taxonomy.get("branch", [])
                
            # Processar cada branch da Taxonomia
            for branch in branches_in_taxonomy:
                branches_processed += 1
                branch_title = branch.get("title")
                
                # Pega os dados da avaliação do branch
                evaluate_data = branch["evaluate"]
                actual_fulfilled = evaluate_data.get("fulfilled")
                actual_feedback = evaluate_data.get("feedback")
                
                if branch_title in expected_output_correto:
                    expected_data = expected_output_correto[branch_title]
                    expected_fulfilled = expected_data["fulfilled"]
                    expected_feedback = expected_data["feedback"]
                    
                    # Verificar se fulfilled está correto
                    # assert actual_fulfilled == expected_fulfilled, \
                    #     f"Fulfilled correto para {branch_title}. Esperado: {expected_fulfilled}, Atual: {actual_fulfilled}"
                    
                    # Criar test_case e adicionar à lista
                    test_case = LLMTestCase(
                        input=f"Avaliar critério: {branch_title}",
                        actual_output=actual_feedback,
                        expected_output=expected_feedback
                    )
                    all_test_cases.append(test_case)
                else:
                    print(f"  ⚠️ Branch '{branch_title}' não está no resultado esperado")
    
    # Definir métricas uma única vez
    precision_metric_correct = GEval(
        name="Precision",
        criteria="Avalie a precisão da análise com base nos critérios esperados.",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT],
        evaluation_steps=[
            "Verifique se o feedback indica corretamente que o critério foi atendido",
            "Verifique se a análise é objetiva e mensurável",
            "Verifique se não há informações contraditórias"
        ]
    )

    # Avaliar todos os test_cases de uma vez
    if all_test_cases:
        print(f"\n🔄 Avaliando {len(all_test_cases)} test_cases com deepeval...")
        evaluate(
            test_cases=all_test_cases, 
            metrics=[
                precision_metric_correct, 
                # correctness_metric, 
                # completeness_metric, 
                # consistency_metric, 
                # clarity, 
                # professionalism, 
                # pii_leakage, 
                # answer_relevancy
            ]
        )
        print(f"✅ Avaliação concluída para {len(all_test_cases)} critérios!")
    else:
        print("⚠️ Nenhum test_case foi criado para avaliação")


@pytest.mark.asyncio
async def test_experiment_llm_incorreto(ai_client, ai_test_data_setup):
    pdf_path = TEST_PDFS_INCORRETOS[0]
    setup_data = ai_test_data_setup
    
    if not os.path.exists(pdf_path):
        pytest.skip(f"Arquivo PDF incorreto não encontrado: {pdf_path}")
    
    with open(pdf_path, 'rb') as f:
        pdf_content = f.read()
        print(f"\n🔄 Processando documento INCORRETO: {Path(pdf_path).name}")

    typification_ids = list(setup_data["typifications"].values())
    
    # Criar documento no sistema
    doc_response = ai_client.post(
        "/doc/",
        json={
            "name": f"Edital de teste INCORRETO - {Path(pdf_path).stem}",
            "identifier": f"INCORRETO-{Path(pdf_path).stem}",
            "description": "Documento para teste de IA - Caso INCORRETO",
            "typification": typification_ids
        }
    )
        
    # Verificar se o documento foi criado com sucesso
    assert doc_response.status_code == 201, f"Erro ao criar documento: {doc_response.text}"
    doc_data = doc_response.json()
    doc_id = doc_data["id"]
    print(f"✅ Documento criado: {doc_id}")

    # Preparar arquivo para upload
    files = {"file": (Path(pdf_path).name, pdf_content, "application/pdf")}
    
    # Processar documento com IA real
    release_response = ai_client.post(
        f"/doc/{doc_id}/release/",
        files=files
    )
    
    # Verificar se o processamento foi bem-sucedido
    assert release_response.status_code == 201, f"Erro no processamento: {release_response.text}"
    release_data = release_response.json()

    # Resultados esperados para documento INCORRETO
    expected_output_incorreto = {
        "Cadastro no SICAF e ramo de atividade compatível": {
            "feedback": "O critério específico Cadastro no SICAF e ramo de atividade compatível NÃO está contemplado no edital",
            "fulfilled": False
        },
        "Condições especiais sobre Micros e Pequenas Empresas": {
            "feedback": "O critério específico sobre as condições para Micros e Pequenas Empresas NÃO está contemplado no edital",
            "fulfilled": False
        }
    }
    
    # Lista para coletar todos os test_cases
    all_test_cases = []
    
    # Processar cada branch do resultado
    branches_processed = 0
    for typification in release_data["taxonomy"]:
        for taxonomy in typification.get("taxonomy", []):
            branches_in_taxonomy = taxonomy.get("branch", [])
            
            # Processar cada branch da Taxonomia
            for branch in branches_in_taxonomy:
                branches_processed += 1
                branch_title = branch.get("title")
                
                # Pega os dados da avaliação do branch
                evaluate_data = branch["evaluate"]
                actual_fulfilled = evaluate_data.get("fulfilled")
                actual_feedback = evaluate_data.get("feedback")
                
                if branch_title in expected_output_incorreto:
                    expected_data = expected_output_incorreto[branch_title]
                    expected_fulfilled = expected_data["fulfilled"]
                    expected_feedback = expected_data["feedback"]
                    
                    # Verificar se fulfilled está correto
                    # assert actual_fulfilled == expected_fulfilled, \
                    #     f"Fulfilled incorreto para {branch_title}. Esperado: {expected_fulfilled}, Atual: {actual_fulfilled}"
                    
                    # Criar test_case e adicionar à lista
                    test_case = LLMTestCase(
                        input=f"Avaliar critério: {branch_title}",
                        actual_output=actual_feedback,
                        expected_output=expected_feedback
                    )
                    all_test_cases.append(test_case)
                else:
                    print(f"  ⚠️ Branch '{branch_title}' não está no resultado esperado")
    
    # Definir métricas uma única vez
    precision_metric_incorrect = GEval(
        name="Precision",
        criteria="Avalie a precisão da análise com base nos critérios esperados.",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT],
        evaluation_steps=[
            "Verifique se o feedback indica corretamente que o critério NÃO foi atendido",
            "Verifique se a análise é objetiva e mensurável",
            "Verifique se não há informações contraditórias"
        ]
    )

    # Avaliar todos os test_cases de uma vez
    if all_test_cases:
        print(f"\n🔄 Avaliando {len(all_test_cases)} test_cases com deepeval...")
        evaluate(
            test_cases=all_test_cases, 
            metrics=[
                precision_metric_incorrect, 
                # correctness_metric, 
                # completeness_metric, 
                # consistency_metric, 
                # clarity, 
                # professionalism, 
                # pii_leakage, 
                # answer_relevancy
            ]
        )
        print(f"✅ Avaliação concluída para {len(all_test_cases)} critérios!")
    else:
        print("⚠️ Nenhum test_case foi criado para avaliação")