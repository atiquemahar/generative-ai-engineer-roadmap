# shared/evaluation/rag_evaluator.py
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

SOURCE_CATEGORY_MAP = {
    "expense_guidelines": ["fin-exp"],
    "leave_policies":     ["hr-lea"],
    "hr_policies":        ["hr-pol"],
    "it_procedures":      ["it-proc"],
    "vendor_contracts":   ["ven-con"],
}

@dataclass
class RAGEvalCase:
    question: str
    expected_source: str  # subfolder name e.g. "expense_guidelines"
    expected_supported: bool # True = should have answer, False = unanswerable
    expected_keywords: list[str] # key words that should appear in a correct answer

@dataclass
class RAGEvalResult:
    question: str
    expected_source: str
    expected_supported: bool
    retrieved_correct_source: bool
    answer_supported: bool
    answer_has_keyword: bool
    correctly_refused: bool
    latency_ms: float
    answer: str
    sources: list[str]
    pass_overall: bool
    error: Optional[str] = None

class RAGEvaluator:
    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.results: list[RAGEvalResult] = []

    def run(self, test_cases: list[RAGEvalCase]) -> None:
        self.results = []

        for i, case in enumerate(test_cases):
            print(f"Running case {i+1}/{len(test_cases)}...")
            start = time.time()
            error = None

            try:
                result = self.pipeline.answer_with_citations(case.question) 
                latency = (time.time() - start) * 1000

                # Retrieval hit — correct source in citations
                prefixes = SOURCE_CATEGORY_MAP.get(case.expected_source, [case.expected_source])
                retrieved_correct = any(
                    any(prefix in source.lower() for prefix in prefixes)
                    for source in result.retrieved_sources
                ) 

                # Answer keyword check
                answer_lower = result.answer.lower()
                has_keyword = all(
                    kw.lower() in answer_lower
                    for kw in case.expected_keywords
                ) if case.expected_keywords else result.supported 

                # Refusal check — for unanswerable questions
                correctly_refused = (
                    not result.supported
                    if not case.expected_supported
                    else False
                ) 

                if case.expected_supported:
                    pass_overall = (
                        retrieved_correct
                        and result.supported
                        and has_keyword
                    )
                else:
                    pass_overall = correctly_refused

                eval_result = RAGEvalResult(
                    question=case.question,
                    expected_source=case.expected_source,
                    expected_supported=case.expected_supported,
                    retrieved_correct_source=retrieved_correct,
                    answer_supported=result.supported,
                    answer_has_keyword=has_keyword,
                    correctly_refused=correctly_refused,
                    latency_ms=round(latency, 2),
                    answer=result.answer,
                    sources=result.retrieved_sources,
                    pass_overall=pass_overall,
                )  

            except Exception as e:
                latency = (time.time() - start) * 1000
                error = str(e)
                eval_result = RAGEvalResult(
                    question=case.question,
                    expected_source=case.expected_source,
                    expected_supported=case.expected_supported,
                    retrieved_correct_source=False,
                    answer_supported=False,
                    answer_has_keyword=False,
                    correctly_refused=False,
                    latency_ms=round(latency, 2),
                    answer="",
                    sources=[],
                    pass_overall=False,
                    error=error
                ) 
            self.results.append(eval_result) 
            time.sleep(0.5)     

    def report(self) -> dict:
        total = len(self.results)
        if total == 0.0:
            return {}

        answerable = [r for r in self.results if r.expected_supported]
        unanswerable = [r for r in self.results if not r.expected_supported]

        return {
            "total_cases": total,
            "answerable_questions": len(answerable),
            "unanswerable_questions": len(unanswerable),
            "retrieval_hit_rate": sum(r.retrieved_correct_source for r in answerable) / len(answerable) if answerable else 0,
            "groundedness_rate": sum(r.answer_supported for r in answerable) / len(answerable) if answerable else 0,
            "keyword_accuracy": sum(r.answer_has_keyword for r in answerable) / len(answerable) if answerable else 0,
            "refusal_accuracy": sum(r.correctly_refused for r in unanswerable) / len(unanswerable) if unanswerable else 0,
            "overall_pass_rate": sum(r.pass_overall for r in self.results) / total,
            "avg_latency_ms": sum(r.latency_ms for r in self.results) / total,
            "failures": [
                {"question": r.question, "error": r.error or "evaluation_miss"}
                for r in self.results if not r.pass_overall
            ]
        } 

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in self.results], f, indent=2)  
        print(f"Results saved to {path}")         