import json
import pickle
import re
from pathlib import Path
from typing import Optional, Union

from rank_bm25 import BM25Okapi


TOKEN_PATTERN = re.compile(r"\b\w+\b")


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


class BM25Index:
    def __init__(self, index_dir: Union[Path, str] = "data/index/bm25") -> None:
        self.index_dir = Path(index_dir)
        self.index_path = self.index_dir / "index.pkl"
        self.docmap_path = self.index_dir / "docmap.json"
        self.index: Optional[BM25Okapi] = None
        self.doc_ids: list[str] = []

    def build(self, docs: list[dict]) -> None:
        if not docs:
            raise ValueError("Cannot build BM25 index from an empty document corpus")

        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.doc_ids = [str(doc["doc_id"]) for doc in docs]
        corpus = [tokenize(f"{doc.get('title', '')} {doc.get('text', '')}") for doc in docs]
        self.index = BM25Okapi(corpus)

        with self.index_path.open("wb") as handle:
            pickle.dump(self.index, handle)

        self.docmap_path.write_text(
            json.dumps({str(pos): doc_id for pos, doc_id in enumerate(self.doc_ids)}, indent=2),
            encoding="utf-8",
        )

    def load(self) -> None:
        if not self.index_path.exists() or not self.docmap_path.exists():
            raise FileNotFoundError("BM25 index artifacts are missing. Rebuild with python -m app.index")

        with self.index_path.open("rb") as handle:
            self.index = pickle.load(handle)

        docmap = json.loads(self.docmap_path.read_text(encoding="utf-8"))
        self.doc_ids = [docmap[str(pos)] for pos in range(len(docmap))]

    def query(self, q: str, top_k: int) -> list[tuple[str, float]]:
        if self.index is None:
            self.load()

        scores = self.index.get_scores(tokenize(q)) if self.index is not None else []
        ranked = sorted(enumerate(scores), key=lambda item: (-float(item[1]), item[0]))[:top_k]
        return [(self.doc_ids[pos], float(score)) for pos, score in ranked]
