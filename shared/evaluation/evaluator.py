import json
import time
from dataclasses import dataclass, asdict
from typing import Optional, Callable

@dataclass
class EvalResult:
    input: str
    expected_intent: str
    expected_priority: str
    expected_customer_id: Optional[str]
    expected_order_id: Optional[str]
    expected_missing_fields: list
    actual_intent: Optional[str]
    actual_priority: Optional[str]
    actual_customer_id: Optional[str]
    actual_order_id: Optional[str]
    schema_valid: bool
    correct_intent: bool
    correct_priority: bool
    correct_customer_id: bool
    correct_order_id: bool
    correct_missing_fields: bool
    latency_ms: float
    pass_overall: bool
    error: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class ComplaintEvaluator:
    def __init__(self, extractor_fn: Callable):
        # extractor_fn must be a single-argument callable: fn(message) -> Complaint
        # Use functools.partial to bind project_client before passing here
        self.extractor_fn = extractor_fn
        self.results: list[EvalResult] = []

    def run(self, test_cases: list[dict]) -> None:
        """
        Each test case dict must have:
        - input: str
        - expected_intent: str
        - expected_priority: str
        - expected_customer_id: str | None
        - expected_order_id: str | None
        - expected_missing_fields: list[str]
        """  
        self.results = []

        for i, case in enumerate(test_cases):
            print(f"Running case {i+1}/{len(test_cases)}...")
            start = time.time()
            error = None
            result = None
            schema_valid = False
            token_usage = {}

            try:
                result = self.extractor_fn(case["input"]) 
                schema_valid = True
                token_usage = getattr(self.extractor_fn, "last_token_usage", {})

            except Exception as e:
                error = str(e)

            latency = (time.time() -start) * 1000

            # Build comparison — write this logic yourself
            # Compare result fields against expected fields
            # If schema_valid is False, all correct_ fields are False
            eval_result = EvalResult(
                input=case["input"],
                expected_intent=case["expected_intent"],
                expected_priority=case["expected_priority"],
                expected_customer_id=case.get("expected_customer_id"),
                expected_order_id=case.get("expected_order_id"),
                expected_missing_fields=case.get("expected_missing_fields", []),
                actual_intent=result.intent if result else None,
                actual_priority=result.priority if result else None,
                actual_customer_id=result.customer_id if result else None,
                actual_order_id=result.order_id if result else None,
                schema_valid=schema_valid,
                correct_intent=result.intent == case["expected_intent"] if result else False,
                correct_priority=result.priority == case["expected_priority"] if result else False,
                correct_customer_id=result.customer_id == case.get("expected_customer_id") if result else False,
                correct_order_id=result.order_id == case.get("expected_order_id") if result else False,
                correct_missing_fields=sorted(result.missing_fields) == sorted(case.get("expected_missing_fields", [])) if result else False,
                latency_ms=round(latency,2),
                pass_overall=False, # set below
                error=error,
                input_tokens=token_usage.get("input_tokens", 0),
                output_tokens=token_usage.get("output_tokens", 0),
                total_tokens=token_usage.get("total_tokens", 0)

            )

            # pass_overall = schema valid + all fields correct
            eval_result.pass_overall = all([
                eval_result.schema_valid,
                eval_result.correct_intent,
                eval_result.correct_priority,
                eval_result.correct_customer_id,
                eval_result.correct_order_id
            ])

            self.results.append(eval_result)
            time.sleep(1) # rate limiting

    def report(self) -> dict:
        """Generate summary metrics from results."""
        total = len(self.results)  
        if total == 0:
            return {}
          
        total_tokens = sum(r.total_tokens for r in self.results)

        return {
            "total_cases": total,
            "schema_validity_rate": sum(r.schema_valid for r in self.results) / total,
            "intent_accuracy": sum(r.correct_intent for r in self.results) / total,
            "priority_accuracy": sum(r.correct_priority for r in self.results) / total,
            "customer_id_accuracy": sum(r.correct_customer_id for r in self.results) / total,
            "order_id_accuracy": sum(r.correct_order_id for r in self.results) / total,
            "overall_pass_rate": sum(r.pass_overall for r in self.results) / total,
            "avg_latency_ms": sum(r.latency_ms for r in self.results) / total,
            "total_tokens_used": total_tokens,
            "avg_tokens_per_call": round(total_tokens/total, 1),
            "estimated_cost_usd": round(total_tokens * 0.000002, 4), #rough estimate
            "failures": [
                {"input": r.input, "error": r.error or "field_mismatch"}
                for r in self.results if not r.pass_overall
            ]
        } 

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in self.results], f, indent=2)
        print(f"Results saved to: {path} ")       



