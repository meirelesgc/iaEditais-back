# Referência da API

Esta seção fornece uma referência técnica e detalhada para todos os endpoints disponíveis na API **iaEditais**.

## Convenções

* Todos os endpoints base seguem o formato `http://localhost:8000`.
* Os tipos de dados são definidos pelos schemas Pydantic encontrados em `iaEditais/schemas/`.
* A autenticação não é abordada nesta documentação inicial.

---

## Source

Recursos para gerenciar as fontes de referência (leis, normas, etc.).

### `POST /source/`

Cria uma nova fonte de referência. Permite o upload opcional de um arquivo PDF.

* **Status**: `201 CREATED`
* **Request Body**: `multipart/form-data`
    * `name`: `string` (required)
    * `description`: `string` (required)
    * `file`: `UploadFile` (optional)
* **Response Body**: `Source`
    ```json
    {
      "id": "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6",
      "name": "string",
      "description": "string",
      "has_file": false,
      "created_at": "2024-01-01T00:00:00.000Z",
      "updated_at": null
    }
    ```

### `GET /source/`

Lista todas as fontes cadastradas.

* **Status**: `200 OK`
* **Response Body**: `list[Source]`

### `GET /source/{source_id}/`

Retorna o arquivo PDF associado a uma fonte.

* **Status**: `200 OK`
* **Path Parameter**: `source_id: UUID`
* **Response Body**: `FileResponse`

### `DELETE /source/{source_id}/`

Exclui uma fonte e seu arquivo associado.

* **Status**: `204 NO CONTENT`
* **Path Parameter**: `source_id: UUID`

---

## Typification

Recursos para gerenciar as tipificações (nível 1 da árvore).

### `POST /typification/`

Cria uma nova tipificação.

* **Status**: `201 CREATED`
* **Request Body**: `CreateTypification`
    ```json
    {
      "name": "string",
      "source": ["a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6"]
    }
    ```
* **Response Body**: `Typification`

### `GET /typification/`

Lista todas as tipificações.

* **Status**: `200 OK`
* **Response Body**: `list[Typification]`

---

## Taxonomy

Recursos para gerenciar a taxonomia (nível 2 da árvore).

### `POST /taxonomy/`

Cria um novo item de taxonomia associado a uma tipificação.

* **Status**: `201 CREATED`
* **Request Body**: `CreateTaxonomy`
    ```json
    {
      "typification_id": "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6",
      "title": "string",
      "description": "string",
      "source": []
    }
    ```
* **Response Body**: `Taxonomy`

### `GET /taxonomy/{typification_id}/`

Lista todos os itens de taxonomia de uma tipificação específica.

* **Status**: `200 OK`
* **Path Parameter**: `typification_id: UUID`
* **Response Body**: `list[Taxonomy]`

---

## Branch

Recursos para gerenciar os ramos (nível 3 da árvore).

### `POST /taxonomy/branch/`

Cria um novo ramo associado a uma taxonomia.

* **Status**: `201 CREATED`
* **Request Body**: `CreateBranch`
    ```json
    {
      "taxonomy_id": "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6",
      "title": "string",
      "description": "string"
    }
    ```
* **Response Body**: `Branch`

### `GET /taxonomy/branch/{taxonomy_id}/`

Lista todos os ramos de uma taxonomia específica.

* **Status**: `200 OK`
* **Path Parameter**: `taxonomy_id: UUID`
* **Response Body**: `list[Branch]`

---

## Doc & Release

Recursos para gerenciar os documentos (editais) e suas análises (releases).

### `POST /doc/`

Cria um novo registro de documento.

* **Status**: `201 CREATED`
* **Request Body**: `CreateDoc`
    ```json
    {
      "name": "Edital de Exemplo",
      "typification": ["a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6"]
    }
    ```
* **Response Body**: `Doc`

### `GET /doc/`

Lista todos os documentos.

* **Status**: `200 OK`
* **Response Body**: `list[Doc]`

### `POST /doc/{doc_id}/release/`

Inicia a análise de um documento. Faz o upload do arquivo PDF e dispara o pipeline RAG.

* **Status**: `201 CREATED`
* **Path Parameter**: `doc_id: UUID`
* **Request Body**: `multipart/form-data`
    * `file`: `UploadFile` (required, `.pdf` only)
* **Response Body**: `Release` (contém a árvore de verificação com os resultados da análise)

### `GET /doc/{doc_id}/release/`

Lista todas as análises (releases) de um documento.

* **Status**: `200 OK`
* **Path Parameter**: `doc_id: UUID`
* **Response Body**: `list[Release]`

### `GET /doc/release/{release_id}/`

Retorna o arquivo PDF de uma análise específica.

* **Status**: `200 OK`
* **Path Parameter**: `release_id: UUID`
* **Response Body**: `FileResponse`