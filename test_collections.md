# CRUD de Test Collections

## Criar Test Collection

**URL:** `/test-collections/`
**Method:** `POST`
**Payload:**

```json
{
  "name": "Coleção de Testes de Licitação - TIC",
  "description": "Coleção de testes focada em editais de Tecnologia da Informação"
}
```

**Response:**

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "Coleção de Testes de Licitação - TIC",
  "description": "Coleção de testes focada em editais de Tecnologia da Informação",
  "created_at": "2024-11-29T10:00:00.000Z",
  "updated_at": null
}
```

## Listar Test Collections

**URL:** `/test-collections/`
**Method:** `GET`
**Payload:**
_(Nenhum payload necessário. Parâmetros de query opcionais: `offset`, `limit`)_
**Response:**

```json
{
  "test_collections": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "Coleção de Testes de Licitação - TIC",
      "description": "Coleção de testes focada em editais de Tecnologia da Informação",
      "created_at": "2024-11-29T10:00:00.000Z",
      "updated_at": null
    }
  ]
}
```

## Detalhar Test Collection

**URL:** `/test-collections/{collection_id}`
**Method:** `GET`
**Payload:**
_(Nenhum payload necessário)_
**Response:**

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "Coleção de Testes de Licitação - TIC",
  "description": "Coleção de testes focada em editais de Tecnologia da Informação",
  "created_at": "2024-11-29T10:00:00.000Z",
  "updated_at": null
}
```

## Atualizar Test Collection

**URL:** `/test-collections/{collection_id}`
**Method:** `PUT`
**Payload:**

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "Coleção de Testes de Licitação - TIC (Atualizado)",
  "description": "Descrição atualizada da coleção"
}
```

**Response:**

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "Coleção de Testes de Licitação - TIC (Atualizado)",
  "description": "Descrição atualizada da coleção",
  "created_at": "2024-11-29T10:00:00.000Z",
  "updated_at": "2024-11-29T10:05:00.000Z"
}
```

## Deletar Test Collection

**URL:** `/test-collections/{collection_id}`
**Method:** `DELETE`
**Payload:**
_(Nenhum payload necessário)_
**Response:**
_(Sem corpo de resposta - Status 204 No Content)_
