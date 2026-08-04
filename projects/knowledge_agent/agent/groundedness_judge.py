"""
projects/knowledge_agent/agent/groundedness_judge.py
Day 22 — semantic overlap groundedness scorer

Groundedness: is the answer supported by the retrieved context?
This implementation uses embeddings + token overlap instead of an LLM judge.
"""
import os
import math
from difflib import SequenceMatcher
from typing import List, Optional

EMBEDDING_MODEL = os.environ.get("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")


def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _parse_context_chunks(context: str) -> List[dict]:
    parts = [p.strip() for p in context.split("\n\n") if p.strip()]
    chunks = []
    for p in parts:
        if "\n" in p:
            first, rest = p.split("\n", 1)
            if "]" in first:
                after = first.split("]", 1)[1].strip()
            else:
                after = first.strip()
            filename = after.split("—", 1)[0].strip()
            chunks.append({"filename": filename, "content": rest.strip()})
        else:
            chunks.append({"filename": "", "content": p})
    return chunks


def _try_get_embeddings(openai_client, texts: List[str]):
    if openai_client is None:
        return None
    try:
        resp = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        data = getattr(resp, "data", None) or (resp.get("data") if isinstance(resp, dict) else None)
        if not data:
            return None
        embeddings = []
        for item in data:
            if isinstance(item, dict):
                embeddings.append(item.get("embedding"))
            else:
                embeddings.append(getattr(item, "embedding", None))
        if any(e is None for e in embeddings):
            return None
        return embeddings
    except Exception:
        return None


def judge_groundedness(
    question: str,
    answer: str,
    context: str,
    openai_client=None,
    evidence: Optional[str] = None,
) -> dict:
    if not answer or not context:
        return {"grounded": False, "score": 0, "reason": "empty answer or context"}

    chunks = _parse_context_chunks(context)
    if not chunks:
        return {"grounded": False, "score": 0, "reason": "no parsed context chunks"}

    if evidence:
        ev = evidence.strip().strip('"').lower()
        for c in chunks:
            fname = (c.get("filename") or "").lower()
            if fname and ev in fname:
                return {"grounded": True, "score": 3, "reason": f"evidence filename match: {ev}"}
        for c in chunks:
            if ev in (c.get("content") or "").lower():
                return {"grounded": True, "score": 3, "reason": f"evidence excerpt exact match: {ev}"}
        for c in chunks:
            snippet = (c.get("content") or "")[: len(ev) + 200]
            if SequenceMatcher(None, ev, snippet.lower()).ratio() >= 0.80:
                return {"grounded": True, "score": 3, "reason": f"evidence excerpt fuzzy match: {ev}"}

    texts = [answer] + [c["content"] for c in chunks]
    embeddings = _try_get_embeddings(openai_client, texts)
    if embeddings:
        ans_emb = embeddings[0]
        chunk_embs = embeddings[1:]
        sims = [_cosine(ans_emb, ce) for ce in chunk_embs]
        max_sim = max(sims) if sims else 0.0
        best_idx = sims.index(max_sim) if sims else 0
        best_chunk = chunks[best_idx]
        reason = f"embedding_max_sim={max_sim:.3f} (best={best_chunk.get('filename')})"
    else:
        answer_lower = answer.lower()
        tokens = [w for w in answer_lower.split() if len(w) > 3]
        scores_fb = []
        for c in chunks:
            content = (c.get("content") or "").lower()
            if not tokens:
                scores_fb.append(0.0)
                continue
            hit_rate = sum(1 for t in tokens if t in content) / len(tokens)
            scores_fb.append(hit_rate)
        max_sim = max(scores_fb) if scores_fb else 0.0
        best_idx = scores_fb.index(max_sim) if scores_fb else 0
        best_chunk = chunks[best_idx]
        reason = f"token_hit_rate={max_sim:.3f} (best={best_chunk.get('filename')})"

    if max_sim >= 0.72:
        score = 3
    elif max_sim >= 0.50:
        score = 2
    elif max_sim >= 0.30:
        score = 1
    else:
        score = 0

    return {"grounded": score >= 2, "score": score, "reason": reason}
