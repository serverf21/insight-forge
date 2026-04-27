import json
import math
from pathlib import Path
from typing import Optional, Protocol, Union

from pydantic import BaseModel

from app.search.bm25 import BM25Index
from app.search.vector import VectorIndex


class SearchBackend(Protocol):
    def query(self, q: str, top_k: int) -> list[tuple[str, float]]:
        ...


class SearchResult(BaseModel):
    doc_id: str
    title: str
    snippet: str
    bm25_score: float
    vector_score: float
    hybrid_score: float


def minmax_normalize(scores: list[float]) -> list[float]:
    if not scores:
        return []

    minimum = min(scores)
    maximum = max(scores)
    if math.isclose(minimum, maximum):
        return [1.0 / len(scores)] * len(scores)

    span = maximum - minimum
    return [(score - minimum) / span for score in scores]


def softmax_normalize(scores: list[float]) -> list[float]:
    if not scores:
        return []

    offset = max(scores)
    exp_scores = [math.exp(score - offset) for score in scores]
    total = sum(exp_scores)
    if total == 0.0 or not math.isfinite(total):
        return [1.0 / len(scores)] * len(scores)

    return [score / total for score in exp_scores]


class HybridSearcher:
    def __init__(
        self,
        docs_path: Union[Path, str] = "data/processed/docs.jsonl",
        bm25_index: Optional[SearchBackend] = None,
        vector_index: Optional[SearchBackend] = None,
    ) -> None:
        self.docs_path = Path(docs_path)
        self.bm25_index = bm25_index or BM25Index()
        self.vector_index = vector_index or VectorIndex()
        self.docs = self._load_docs(self.docs_path)

    def search(self, query: str, top_k: int = 10, alpha: float = 0.5) -> list[SearchResult]:
        if not 0.0 <= alpha <= 1.0:
            raise ValueError("alpha must be between 0.0 and 1.0")
        if top_k <= 0:
            return []

        candidate_k = top_k * 3
        bm25_scores = dict(self.bm25_index.query(query, candidate_k))
        vector_scores = dict(self.vector_index.query(query, candidate_k))
        candidate_ids = list(dict.fromkeys([*bm25_scores.keys(), *vector_scores.keys()]))

        bm25_raw = [float(bm25_scores.get(doc_id, 0.0)) for doc_id in candidate_ids]
        vector_raw = [float(vector_scores.get(doc_id, 0.0)) for doc_id in candidate_ids]
        bm25_norm = minmax_normalize(bm25_raw)
        vector_norm = minmax_normalize(vector_raw)

        results = []
        for idx, doc_id in enumerate(candidate_ids):
            doc = self.docs.get(doc_id, {})
            bm25_score = bm25_raw[idx]
            vector_score = vector_raw[idx]
            hybrid_score = alpha * bm25_norm[idx] + (1.0 - alpha) * vector_norm[idx]
            results.append(
                SearchResult(
                    doc_id=doc_id,
                    title=str(doc.get("title", "")),
                    snippet=str(doc.get("text", ""))[:200],
                    bm25_score=bm25_score,
                    vector_score=vector_score,
                    hybrid_score=hybrid_score,
                )
            )

        return sorted(results, key=lambda result: (-result.hybrid_score, result.doc_id))[:top_k]

    @staticmethod
    def _load_docs(path: Path) -> dict[str, dict]:
        docs = {}
        if not path.exists():
            return docs

        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            doc = json.loads(line)
            docs[str(doc["doc_id"])] = doc
        return docs
