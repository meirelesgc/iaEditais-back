# Test Runs

## Execute Test Run

**url:** /test-runs/

**method:** POST

**payload:**
Multipart Form Data:
- `payload`: JSON string
  ```json
  {
    "test_collection_id": "uuid",  // Optional if test_case_id is provided
    "test_case_id": "uuid",        // Optional if test_collection_id is provided
    "metric_ids": ["uuid1", "uuid2"],
    "model_id": "uuid"             // Optional, defaults to first available model
  }
  ```
- `file`: PDF file

**response:**
```json
{
  "test_run_id": "uuid",
  "test_collection_id": "uuid",
  "case_count": 10,
  "metric_count": 2,
  "results": [
    {
      "test_case_id": "uuid",
      "metric_id": "uuid",
      "result_id": "uuid",
      "passed": true,
      "score": 0.95
    }
  ]
}
```

