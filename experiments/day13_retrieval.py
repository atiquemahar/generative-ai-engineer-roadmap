"""
Day 13 — First Complete RAG Pipeline
 
Every step is explicit:
  retrieve → build_context → prompt → call model → return structured response
 
Loads the FAISS index saved on Day 12 — no re-embedding needed.
"""

import os
import sys
import time
import json
from pathlib import Path
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import AzureOpenAIEmbeddings
from openai import AzureOpenAI
from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")

client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version="2025-04-01-preview",
)    


SYSTEM_PROMPT = """You are a helpful HR and policy assistant for NovaTech Enterprises.
Answer questions based ONLY on the provided context documents.
If the context does not contain enough information to answer, say exactly:
"I don't have enough information in the provided documents to answer this question."
Never make up information not present in the context.
Be concise and specific — quote exact figures, dates, or thresholds when available."""

class RAGPipeline:
    def __init__(self, vectorstore: FAISS):
        self.vectorstore = vectorstore
        self.client = client

    def retrieve(self, query: str, k: int =3) -> list[Document]:
        """Step 1 — vector similarity search against FAISS index."""
        return self.vectorstore.similarity_search(query, k=k)
     
    def build_context(self, docs: list[Document]) -> str:
        """Step 2 — format retrieved chunks into numbered context block."""
        parts = []
        for i, doc in enumerate(docs, 1):
            filename = doc.metadata.get("filename", doc.metadata.get("source", "unknown")) 
            parts.append(f"[{i}] source: {filename}\n{doc.page_content}")
        return "\n\n".join(parts)      
    
    def answer(self, query: str) -> dict:
        """Step 3 — retrieve → build context → call model → return structured response."""

        # Step 3a: retrieve
        retrieved = self.retrieve(query)
        if not retrieved:
            return {
                "answer": "I don't have enough information to answer this question.",
                "sources": [],
                "supported": False,
                "chunks_used": 0,
            }
        
        # Step 3b: build context
        context = self.build_context(retrieved)

        # Step 3c: build prompt
        user_input = f"""Context documents:{context}
                        Question: {query}
                    Answer based only on the context above.""" 
         

        #Step 3d: call model 
        response = self.client.responses.create(
            model=os.environ["MODEL_DEPLOYMENT_NAME"],
            instructions=SYSTEM_PROMPT,
            input=user_input,
            max_output_tokens=500,
        )  

        # Step 3e: return structured response
        return {
            "answer": response.output_text.strip(),
            "sources": [Path(doc.metadata.get("filename") or doc.metadata.get("source", "unknown")).name for doc in retrieved],
            "supported": True,
            "chunks_used": len(retrieved),
        }   
    
def load_vectorstore() -> FAISS:
    index_path = Path(REPO_ROOT) / "experiments" / "retrieval" / "faiss_index"
    if not index_path.exists():
        raise  FileNotFoundError(
            f"FAISS index not found at {index_path}.\n"
            "Run day12_vector_search.py first to build and save the index."
        )    
    embeddings = AzureOpenAIEmbeddings(
        azure_deployment=os.environ["AZURE_EMBEDDING_DEPLOYMENT"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        openai_api_version="2025-04-01-preview",
    )
    return FAISS.load_local(
        str(index_path),
        embeddings,
        allow_dangerous_deserialization=True,  # safe — our own index 
    )

QUESTIONS = [
    {"question": "What is the maximum expense claim without a receipt?",
     "expected_source": "expense_guidelines"},
    {"question": "How many days of annual leave does a new employee get?",
     "expected_source": "leave_policies"},
    {"question": "What VPN software is approved for remote access?",
     "expected_source": "it_procedures"},
    {"question": "How much fee will the customer pay to the Vendor monthly?",
     "expected_source": "vendor_contracts"},
    {"question": "After how many days of invoice will payment be due?",
     "expected_source": "vendor_contracts"},
    {"question": "How many days of Paid Sick Leave does an employee with 3 years experience get?",
     "expected_source": "leave_policies"},
    {"question": "What is the code of conduct for Social Media and public Communication?",
     "expected_source": "hr_policies"},
    {"question": "What is the Shortlisting criteria?",
     "expected_source": "hr_policies"},
    {"question": "What is the Offer and Onboarding policy?",
     "expected_source": "hr_policies"},
    {"question": "Within how many days must expenses be submitted after they are incurred?",
     "expected_source": "expense_guidelines"},
    {"question": "What is the personal car mileage reimbursement rate?",
     "expected_source": "expense_guidelines"},
    {"question": "What is the one-time home office setup allowance for remote workers?",
     "expected_source": "expense_guidelines"},
    {"question": "What monthly internet stipend is provided to approved remote workers?",
     "expected_source": "expense_guidelines"},
    {"question": "What is the annual professional development budget for an individual contributor?",
     "expected_source": "expense_guidelines"},
    {"question": "How much bonus does NovaTech pay for passing an associate-level certification exam?",
     "expected_source": "expense_guidelines"},
    {"question": "After how many consecutive days of absence must an employee submit a medical certificate?",
     "expected_source": "leave_policies"},
    {"question": "How many Keeping in Touch days can an employee work during parental leave?",
     "expected_source": "leave_policies"},
    {"question": "What uptime percentage does the vendor guarantee for production workloads?",
     "expected_source": "vendor_contracts"},
    {"question": "Where must customer data be stored under the data protection clause?",
     "expected_source": "vendor_contracts"},
    {"question": "What is the response SLA for a P1 Critical IT incident?",
     "expected_source": "it_procedures"},
]

SOURCE_CATEGORY_MAP = {
    "expense_guidelines": ["FIN-EXP"],
    "leave_policies":     ["HR-LEA"],
    "hr_policies":        ["HR-POL"],
    "it_procedures":      ["IT-PROC"],
    "vendor_contracts":   ["VEN-CON"],
}
def check_source_hit(sources: list[str], expected: str) -> bool:
    prefixes = SOURCE_CATEGORY_MAP.get(expected, [])

    return any(
        prefix.casefold() in source.casefold()
        for prefix in prefixes
        for source in sources
    )
    # return any(expected.lower() in s.lower() for s in sources)

def check_answered(answer: str) -> bool:
    """
    Simple heuristic: flag if answer contains no-information phrases
    that suggest the model couldn't find the answer.
    A real hallucination check (Day 14) compares answer against retrieved text.
    """
    no_info_phrases = [
        "i don't have enough information",
        "cannot answer this question",
        "not mentioned in the provided",
        "not provided in the context",
    ]
    answer_lower = answer.lower().strip()
    return not any(phrase in answer_lower for phrase in no_info_phrases)

if __name__ == "__main__":
    print("Loading FAISS index from Day 12...")
    vectorstore = load_vectorstore()
    pipeline = RAGPipeline(vectorstore)
    print("Pipeline ready.\n")

    results = []
    source_hits = 0
    answered = 0

    print(f"{'='*70}")
    print(f"{'#':<3} {'Question':<44} {'Src':>4} {'Ans':>4}")
    print(f"{'-'*70}")

    for i, qa in enumerate(QUESTIONS):
        try:
            result = pipeline.answer(qa["question"])
            time.sleep(0.5)  # avoid rate limits

            src_hit = check_source_hit(result["sources"], qa["expected_source"])
            has_answer = result["supported"] and check_answered(result["answer"])

            if src_hit:   source_hits += 1
            if has_answer: answered += 1
 
            src_str = "✓" if src_hit   else "✗"
            ans_str = "✓" if has_answer else "✗"

            print(f"{i+1:<3} {qa['question'][:43]:<44} {src_str:>4} {ans_str:>4}")

            results.append({
                "question":        qa["question"],
                "expected_source": qa["expected_source"],
                "answer":          result["answer"],
                "sources":         result["sources"],
                "chunks_used":     result["chunks_used"],
                "source_hit":      src_hit,
                "has_answer":      has_answer,
            })
        
        except Exception as e:
            print(f"{i+1:<3} {qa['question'][:43]:<44} {'ERR':>4} {'ERR':>4}  ← {e}")
            results.append({
                "question": qa["question"],
                "error": str(e),
                "source_hit": False,
                "has_answer": False,
            })

    print(f"{'-'*70}")
    print(f"{'TOTAL':<48} {source_hits}/20 {answered}/20")
    print(f"\n  Src = retrieved from correct document category")
    print(f"  Ans = model produced a grounded answer (not 'no info')") 

     # ── Print a few answers for inspection ───────────────────────────────────
    print(f"\n{'='*70}")
    print("SAMPLE ANSWERS (first 5)")
    print(f"{'='*70}")
    for r in results[:5]:
        if "error" in r:
            continue
        print(f"\nQ: {r['question']}")
        print(f"A: {r['answer']}")
        print(f"Sources: {r['sources']}")
        print(f"Chunks used: {r['chunks_used']}")
 
    # ── Save results for Day 14 hallucination analysis ────────────────────────
    output_path = REPO_ROOT / "experiments" / "day13_rag_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")
    print("(Day 14 will load this file for citation + hallucination checks)")           