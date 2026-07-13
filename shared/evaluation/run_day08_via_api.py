import os
import json
import time
import httpx
from shared.models.complaint import Complaint
from shared.evaluation.evaluator import ComplaintEvaluator

BASE_URL = "http://127.0.0.1:8000"

def api_extractor(message: str) -> Complaint:
    """Call the /extract/ endpoint instead of the function directly."""
    response = httpx.post(
        f"{BASE_URL}/extract/",
        json={"text_to_analyze": message},
        timeout=30.0
    )
    if response.status_code != 200:
        raise Exception(f"API error {response.status_code}: {response.text}")
    return Complaint(**response.json())

if __name__ == "__main__":
    eval_path = os.path.join("evaluations", "day07_baseline.json")
    with open(eval_path) as f:
        test_cases = json.load(f)

    evaluator = ComplaintEvaluator(extractor_fn=api_extractor)    
    evaluator.run(test_cases)

    report = evaluator.report()
    print("\n" + "="*50)
    print("EVALUATION REPORT - VIA API")
    print("="*50)
    for key, value in report.items():
        if key != "failures":
            print(f"{key:30s}: {value}")

    result_path = os.path.join("evaluations", "day08_api_results.json")        
    evaluator.save(result_path)