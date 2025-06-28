# Referência da API

Esta seção fornece uma descrição técnica detalhada dos endpoints da API, incluindo rotas, schemas e as operações de negócio correspondentes.

## Estrutura Geral

A API está organizada em torno de quatro recursos principais: `Source`, `Tree`, `Doc` e `Release`. A estrutura da árvore de verificação é dividida em `Typification`, `Taxonomy` e `Branch`.

---

## Endpoint: Source

Gerencia as fontes de informação (ex: leis, normas) que fundamentam os critérios de análise.

### `POST /source/`

Cria uma nova fonte de informação. Opcionalmente, pode receber um arquivo PDF.

- **Request Body**:
    - `name` (str): Nome da fonte.
    - `description` (str): Descrição da fonte.
    - `file` (UploadFile, opcional): Arquivo PDF associado à fonte.
- **Response Model**: `iaEditais.models.source.Source`
- **Status Code**: `201 CREATED`

### `GET /source/`

Retorna a lista de todas as fontes cadastradas.

- **Response Model**: `list[iaEditais.models.source.Source]`
- **Status Code**: `200 OK`

### `GET /source/{source_id}/`

Retorna o arquivo PDF associado a uma fonte específica.

- **Path Parameter**: `source_id` (UUID).
- **Response Class**: `FileResponse`
- **Status Code**: `200 OK`

### `PUT /source/`

Atualiza os dados de uma fonte.

- **Request Body**: `iaEditais.models.source.Source`
- **Response Model**: `iaEditais.models.source.Source`
- **Status Code**: `200 OK`

### `DELETE /source/{source_id}/`

Deleta uma fonte e seu arquivo associado.

- **Path Parameter**: `source_id` (UUID).
- **Status Code**: `204 NO CONTENT`

---

## Endpoint: Tree

Gerencia a estrutura da árvore de verificação, composta por `Typification`, `Taxonomy` e `Branch`.

### Tipificação (`/typification/`)

Representa a categoria geral de um edital (ex: "Contratação Direta").

- **`POST /typification/`**: Cria uma nova tipificação.
    - **Request Model**: `iaEditais.models.typification.CreateTypification`
    - **Response Model**: `iaEditais.models.typification.Typification`
- **`GET /typification/`**: Retorna todas as tipificações.
    - **Response Model**: `list[iaEditais.models.typification.Typification]`
- **`GET /typification/{typification_id}/`**: Retorna uma tipificação específica.
    - **Response Model**: `iaEditais.models.typification.Typification`
- **`PUT /typification/`**: Atualiza uma tipificação.
    - **Request Model**: `iaEditais.models.typification.Typification`
    - **Response Model**: `iaEditais.models.typification.Typification`
- **`DELETE /typification/{typification_id}/`**: Deleta uma tipificação.
    - **Status Code**: `204 NO CONTENT`

### Taxonomia (`/taxonomy/`)

Representa os critérios principais de análise dentro de uma tipificação.

- **`POST /taxonomy/`**: Cria uma nova taxonomia.
    - **Request Model**: `iaEditais.models.taxonomy.CreateTaxonomy`
    - **Response Model**: `iaEditais.models.taxonomy.Taxonomy`
- **`GET /taxonomy/{typification_id}/`**: Retorna as taxonomias de uma tipificação.
    - **Response Model**: `list[iaEditais.models.taxonomy.Taxonomy]`
- **`PUT /taxonomy/`**: Atualiza uma taxonomia.
    - **Request Model**: `iaEditais.models.taxonomy.Taxonomy`
    - **Response Model**: `iaEditais.models.taxonomy.Taxonomy`
- **`DELETE /taxonomy/{taxonomy_id}/`**: Deleta uma taxonomia.
    - **Status Code**: `204 NO CONTENT`

### Ramificação (`/taxonomy/branch/`)

Representa os critérios específicos (perguntas) a serem verificados em uma taxonomia.

- **`POST /taxonomy/branch/`**: Cria uma nova ramificação.
    - **Request Model**: `iaEditais.models.branch.CreateBranch`
    - **Response Model**: `iaEditais.models.branch.Branch`
- **`GET /taxonomy/branch/{taxonomy_id}/`**: Retorna as ramificações de uma taxonomia.
    - **Response Model**: `list[iaEditais.models.branch.Branch]`
- **`PUT /taxonomy/branch/`**: Atualiza uma ramificação.
    - **Request Model**: `iaEditais.models.branch.Branch`
    - **Response Model**: `iaEditais.models.branch.Branch`
- **`DELETE /taxonomy/branch/{branch_id}/`**: Deleta uma ramificação.
    - **Status Code**: `204 NO CONTENT`

---

## Endpoint: Doc

Gerencia os documentos (editais) a serem analisados.

### `POST /doc/`

Cria um novo documento para análise, associando-o a uma ou mais tipificações.

- **Request Model**: `iaEditais.models.doc.CreateDoc`
- **Response Model**: `iaEditais.models.doc.Doc`
- **Status Code**: `201 CREATED`

### `GET /doc/`

Retorna a lista de todos os documentos.

- **Response Model**: `list[iaEditais.models.doc.Doc]`
- **Status Code**: `200 OK`

### `DELETE /doc/{doc_id}/`

Deleta um documento.

- **Path Parameter**: `doc_id` (UUID).
- **Status Code**: `204 NO CONTENT`

---

## Endpoint: Release

Gerencia as análises (releases) de um edital.

### `POST /doc/{doc_id}/release/`

Inicia uma nova análise para um documento. O processo envolve:
1.  Receber o arquivo PDF do edital.
2.  Construir a árvore de verificação com base nas tipificações associadas ao documento.
3.  Adicionar os fragmentos do PDF a um banco de dados vetorial (`PGVector`).
4.  Executar a análise RAG, onde para cada ramificação (`branch`), o sistema busca trechos relevantes no edital e submete a um LLM (`gpt-4o-mini`) para avaliação.
5.  Persistir o resultado da análise no banco de dados.

- **Path Parameter**: `doc_id` (UUID).
- **Request Body**: `file` (UploadFile).
- **Response Model**: `iaEditais.models.doc.Release`
- **Status Code**: `201 CREATED`

### `GET /doc/{doc_id}/release/`

Retorna o histórico de análises de um documento.

- **Path Parameter**: `doc_id` (UUID).
- **Response Model**: `list[iaEditais.models.doc.Release]`
- **Status Code**: `200 OK`

### `GET /doc/release/{release_id}/`

Retorna o arquivo PDF de uma análise específica.

- **Path Parameter**: `release_id` (UUID).
- **Response Class**: `FileResponse`
- **Status Code**: `200 OK`

### `DELETE /doc/release/{release_id}/`

Deleta uma análise específica.

- **Path Parameter**: `release_id` (UUID).
- **Status Code**: `204 NO CONTENT`