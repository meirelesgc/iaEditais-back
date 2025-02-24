# Analisando os editais

## RAG (Retrieval-Augmented Generation)?  

RAG (*Retrieval-Augmented Generation*) é uma abordagem que combina recuperação de informações com geração de texto para melhorar a precisão e relevância das respostas de modelos de linguagem. Em vez de confiar apenas no conhecimento pré-treinado do modelo, o RAG busca informações relevantes em uma base de dados antes de gerar uma resposta. Isso permite que o modelo forneça respostas mais precisas, especialmente em domínios específicos como o de análise de editais. Essa é a base para a implementação das verificações iaEditais.

A técnica funciona em duas etapas principais:  

1. **Recuperação de Documentos:** O sistema busca trechos relevantes de documentos previamente armazenados.  
2. **Geração de Respostas:** O modelo de linguagem usa as informações recuperadas para gerar uma resposta mais informada e contextualizada.

---

## Como o RAG é aplicado na análise de editais?  

O código implementa o RAG para realizar a análise automatizada de editais seguindo os seguintes passos:

### 1. **Carregamento e Armazenamento do Edital**  

Quando um edital é carregado, ele é dividido em pequenos trechos (*chunks*), que são armazenados em um banco vetorial. Isso permite que o modelo encontre fragmentos específicos do documento durante a análise.  

- O arquivo PDF do edital é carregado e transformado em texto.  
- Esse texto é dividido em pedaços.  
- Cada trecho recebe um identificador único para rastrear sua posição no documento original.  
- Os trechos são armazenados em um banco de dados vetorial.  

### 2. **Recuperação de Informação**

Quando um critério de análise precisa ser avaliado, o sistema busca os trechos mais relevantes do edital usando um mecanismo de busca semântica.  

- O critério de análise é transformado em uma consulta (*query*).  
- O banco vetorial realiza uma busca por similaridade para encontrar os trechos mais relevantes do edital.  
- Apenas os trechos mais relevantes são passados para o modelo de linguagem, garantindo que ele analise informações contextualizadas e não partes irrelevantes do documento.  

### 3. **Geração e Avaliação de Respostas**  

Com os trechos relevantes do edital em mãos, o modelo de linguagem é solicitado a avaliar se o critério analisado está presente, qual sua relevância e se há necessidade de ajustes.

- Um **prompt estruturado** é usado para guiar o modelo. Esse prompt fornece o contexto necessário e define as perguntas que o modelo deve responder.  
- O modelo de linguagem recebe os trechos extraídos e gera uma resposta estruturada, indicando:  
  1. Se o critério foi identificado no edital.  
  2. Se o critério está bem detalhado ou se precisa de ajustes.  
  3. Recomendações para melhorar a redação do edital, caso necessário.  

- A resposta gerada é validada e armazenada junto ao critério analisado.  

---

## **Melhores Práticas para Utilização do Processo**  

Para obter o máximo benefício da metodologia de análise de editais, siga estas etapas:  

### **1. Estruturar a Árvore de Verificação**  

Antes de iniciar a análise, certifique-se de que a árvore de verificação está bem definida. Para isso, é necessário:  

- **Definir a tipificação do edital**, garantindo que os critérios de análise sejam compatíveis com a legislação aplicável. Sempre que possível, incluir o arquivo de referência para essa tipificação, pois os dados fornecidos diretamente ao modelo são mais confiáveis do que aqueles provenientes do treinamento.  

- **Organizar a taxonomia**, estruturando os critérios de forma lógica para facilitar a segmentação da análise. Especificar a fonte na qual essa taxonomia se baseia contribui para respostas mais precisas.  

- **Detalhar as ramificações**, garantindo que cada critério contenha perguntas claras e objetivas. Cada ramo deve levar a um único resultado por pergunta (de forma temporária).  

### **2. Revisar e Refinar o Feedback**  

- Avaliar as respostas geradas pelo modelo e utilizá-las para revisar o edital de maneira estruturada.  
- Se necessário, ajustar os critérios ou refinar a árvore de verificação para aprimorar a precisão das análises futuras.  

### **3. Iterar e Aperfeiçoar**  

- Os resultados de cada nova análise podem ser utilizados para aprimorar o modelo e a base de critérios, promovendo a melhoria contínua do processo.  
