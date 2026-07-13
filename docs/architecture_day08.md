docs/architecture-day08.md

## What Was Built in Phase 1 (Days 1-8)



HTTP Client
    │
    ▼
FastAPI (api/main.py)
    │ middleware: trace_id, latency logging
    │ exception handlers: 422, 500
    ▼
/extract/ route (api/routers/extract.py)
    │ dependency injection: get_project_client()
    ▼
extract_complaint() (services/extractor.py)
    │ system prompt: v3_fewshot
    │ retry logic: max 2 retries
    │ json_object format enforcement
    ▼
AIProjectClient → responses.create()
    │ DefaultAzureCredential (az login)
    ▼
Azure AI Foundry (Responses API)
    │
    ▼
Complaint (Pydantic model)
    │ validators: normalize_intent, normalize_confidence
    │ field validation: customer_id starts with C
    ▼
HTTP Response (JSON)

## Evaluation Layer

ComplaintEvaluator
    │ 20 test cases in day07_baseline.json
    │ measures: intent, priority, customer_id, order_id, missing_fields
    ▼
day07_results.json / day08_api_results.json

## Key Numbers

Direct call evaluator (day07):
  overall_pass_rate    : 0.95
  avg_latency_ms       : 8040ms
  total_tokens_used    : 14640
  avg_tokens_per_call  : 732
  estimated_cost_usd   : $0.0293 per 20 calls

API evaluator (day08):
  overall_pass_rate    : 0.95  ← matches direct call exactly
  avg_latency_ms       : 8314ms
  HTTP overhead        : ~274ms (~3.4% increase)
  tokens               : 0 (cross-process limitation — documented)

## Known Limitations
- Token tracking shows 0 in API evaluator (run_day08_via_api.py) because 
  the global token accumulator in services/extractor.py is not accessible 
  across process boundaries. Token data is captured in direct call evaluator 
  (day07_results.json). Full API token tracking planned for Day 22 RAG evaluation.

## Future Improvements
- Return token usage in API response for accurate cost tracking via API evaluator
  (planned for Day 22 RAG evaluation)