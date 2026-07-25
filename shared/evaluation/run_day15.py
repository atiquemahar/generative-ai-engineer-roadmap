import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import AzureOpenAIEmbeddings
from openai import AzureOpenAI

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")

from shared.evaluation.rag_evaluator import RAGEvaluator, RAGEvalCase
from experiments.day15_mmr_retrieval import CitationRAGPipeline, loadPipeline

if __name__ == "__main__":
    # Load test cases
    cases_path = Path(REPO_ROOT) / "shared" / "evaluation" / "rag_baseline_cases.json"
    with open(cases_path) as f:
        raw = json.load(f)
    test_cases = [RAGEvalCase(**c) for c in raw]  

    pipeline = loadPipeline() 
    evaluator = RAGEvaluator(pipeline) 
    evaluator.run(test_cases)

    report = evaluator.report()

    print("\n" + "="*55)
    print("RAG BASELINE EVALUATION REPORT")
    print("="*55)
    for key, value in report.items():
        if key != "failures":
            print(f"{key:<35}: {value}")

    print(f"\nFailures ({len(report['failures'])}):")
    for f in report["failures"]:
        print(f"  - {f['question'][:60]}...")

    evaluator.save(str(REPO_ROOT / "evaluations" / "rag_baseline.json"))