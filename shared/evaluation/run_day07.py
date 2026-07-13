import os
import json
from functools import partial
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

import sys
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from projects.knowledge_agent.services.extractor import extract_complaint
from shared.evaluation.evaluator import ComplaintEvaluator
from shared.models.complaint import Complaint

load_dotenv()

if __name__ == "__main__":
    # Load test cases
    eval_path = os.path.join(REPO_ROOT, "evaluations", "day07_baseline.json")
    with open(eval_path, "r") as f:
        test_cases = json.load(f)

    # Build client and bind to extractor
    project_client = AIProjectClient(
        endpoint=os.environ["AZURE_PROJECT_ENDPOINT"],
        credential=DefaultAzureCredential()
    )   
    def extractor_with_token_tracking(message: str) -> Complaint:
        """Unpacks tuple, stores token usage as function attribute."""
        result, token_usage = extract_complaint(message, project_client=project_client)
        extractor_with_token_tracking.last_token_usage = token_usage
        return result

    extractor_with_token_tracking.last_token_usage = {}

    # Run evaluation
    evaluator = ComplaintEvaluator(extractor_fn=extractor_with_token_tracking)
    evaluator.run(test_cases)

    # Print report
    report = evaluator.report()
    print("\n" + "="*50)
    print("EVALUATION REPORT")
    print("="*50)
    for key, value in report.items():
        if key != "failures":
            print(f"{key:30s}: {value}")

    print(f"\nFailures ({len(report['failures'])}):")
    for f in report["failures"]:
        print(f"  - {f['input'][:60]}... → {f['error']}")

    # Save results
    results_path = os.path.join(REPO_ROOT, "evaluations", "day07_results.json")
    evaluator.save(results_path)    
