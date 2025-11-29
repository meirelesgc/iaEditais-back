# CRUD de Metrics

## Criar Métrica

**URL:** `/metrics/`
**Method:** `POST`
**Payload:**
```json
{
  "name": "Conformidade Técnica",
  "criteria": "Verificar se todos os requisitos técnicos foram atendidos",
  "evaluation_steps": "1. Ler requisitos\n2. Comparar com proposta",
  "threshold": 0.7
}
```
**Response:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "name": "Conformidade Técnica",
  "criteria": "Verificar se todos os requisitos técnicos foram atendidos",
  "evaluation_steps": "1. Ler requisitos\n2. Comparar com proposta",
  "threshold": 0.7,
  "created_at": "2024-11-29T10:00:00.000Z",
  "updated_at": null
}
```

## Listar Métricas

**URL:** `/metrics/`
**Method:** `GET`
**Payload:**
*(Nenhum payload necessário. Parâmetros de query opcionais: `offset`, `limit`)*
**Response:**
```json
{
  "metrics": [
    {
      "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
      "name": "Conformidade Técnica",
      "criteria": "Verificar se todos os requisitos técnicos foram atendidos",
      "evaluation_steps": "1. Ler requisitos\n2. Comparar com proposta",
      "threshold": 0.7,
      "created_at": "2024-11-29T10:00:00.000Z",
      "updated_at": null
    }
  ]
}
```

## Detalhar Métrica

**URL:** `/metrics/{metric_id}`
**Method:** `GET`
**Payload:**
*(Nenhum payload necessário)*
**Response:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "name": "Conformidade Técnica",
  "criteria": "Verificar se todos os requisitos técnicos foram atendidos",
  "evaluation_steps": "1. Ler requisitos\n2. Comparar com proposta",
  "threshold": 0.7,
  "created_at": "2024-11-29T10:00:00.000Z",
  "updated_at": null
}
```

## Atualizar Métrica

**URL:** `/metrics/{metric_id}`
**Method:** `PUT`
**Payload:**
```json
{
  "name": "Conformidade Técnica (Revisada)",
  "criteria": "Verificar requisitos técnicos mandatórios",
  "evaluation_steps": "1. Ler requisitos mandatórios\n2. Comparar com proposta",
  "threshold": 0.8
}
```
**Response:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "name": "Conformidade Técnica (Revisada)",
  "criteria": "Verificar requisitos técnicos mandatórios",
  "evaluation_steps": "1. Ler requisitos mandatórios\n2. Comparar com proposta",
  "threshold": 0.8,
  "created_at": "2024-11-29T10:00:00.000Z",
  "updated_at": "2024-11-29T10:30:00.000Z"
}
```

## Deletar Métrica

**URL:** `/metrics/{metric_id}`
**Method:** `DELETE`
**Payload:**
*(Nenhum payload necessário)*
**Response:**
*(Sem corpo de resposta - Status 204 No Content)*

