# Test Cases API

## Create Test Case

**URL:** `/test-cases/`
**Method:** `POST`
**Payload:**

```json
{
  "name": "Test Case 1",
  "test_collection_id": "uuid-of-test-collection",
  "doc_id": "uuid-of-document",
  "branch_id": "uuid-of-branch",
  "input": "Input for the test case",
  "expected_feedback": "Expected feedback from the model",
  "expected_fulfilled": true
}
```

**Response:**

```json
{
  "id": "uuid-of-new-test-case",
  "name": "Test Case 1",
  "test_collection_id": "uuid-of-test-collection",
  "doc_id": "uuid-of-document",
  "branch_id": "uuid-of-branch",
  "input": "Input for the test case",
  "expected_feedback": "Expected feedback from the model",
  "expected_fulfilled": true,
  "created_at": "2023-10-27T10:00:00Z",
  "updated_at": null
}
```

## List Test Cases

**URL:** `/test-cases/`
**Method:** `GET`
**Payload:** None
**Response:**

```json
{
  "test_cases": [
    {
      "id": "uuid-of-test-case",
      "name": "Test Case 1",
      "test_collection_id": "uuid-of-test-collection",
      "doc_id": "uuid-of-document",
      "branch_id": "uuid-of-branch",
      "input": "Input for the test case",
      "expected_feedback": "Expected feedback from the model",
      "expected_fulfilled": true,
      "created_at": "2023-10-27T10:00:00Z",
      "updated_at": null
    }
  ]
}
```

## Get Test Case

**URL:** `/test-cases/{test_case_id}`
**Method:** `GET`
**Payload:** None
**Response:**

```json
{
  "id": "uuid-of-test-case",
  "name": "Test Case 1",
  "test_collection_id": "uuid-of-test-collection",
  "doc_id": "uuid-of-document",
  "branch_id": "uuid-of-branch",
  "input": "Input for the test case",
  "expected_feedback": "Expected feedback from the model",
  "expected_fulfilled": true,
  "created_at": "2023-10-27T10:00:00Z",
  "updated_at": null
}
```

## Update Test Case

**URL:** `/test-cases/{test_case_id}`
**Method:** `PUT`
**Payload:**

```json
{
  "name": "Updated Test Case Name",
  "input": "Updated input",
  "expected_fulfilled": false,
  "branch_id": "uuid-of-new-branch"
}
```

**Response:**

```json
{
  "id": "uuid-of-test-case",
  "name": "Updated Test Case Name",
  "test_collection_id": "uuid-of-test-collection",
  "doc_id": "uuid-of-document",
  "branch_id": "uuid-of-new-branch",
  "input": "Updated input",
  "expected_feedback": "Expected feedback from the model",
  "expected_fulfilled": false,
  "created_at": "2023-10-27T10:00:00Z",
  "updated_at": "2023-10-27T11:00:00Z"
}
```

## Delete Test Case

**URL:** `/test-cases/{test_case_id}`
**Method:** `DELETE`
**Payload:** None
**Response:** `204 No Content`
