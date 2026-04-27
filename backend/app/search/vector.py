import hashlib
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

import numpy as np


DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"


class VectorIndex:
    def __init__(
        self,
        index_dir: Union[Path, str] = "data/index/vector",
        model_name: str = DEFAULT_MODEL_NAME,
        model: Optional[Any] = None,
    ) -> None:
        self.index_dir = Path(index_dir)
        self.index_path = self.index_dir / "index.faiss"
        self.docmap_path = self.index_dir / "docmap.json"
        self.meta_path = self.index_dir / "meta.json"
        self.model_name = model_name
        self._model = model
        self.index: Optional[Any] = None
        self.doc_ids: list[str] = []

    @property
    def model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name, device="cpu")
        return self._model

    def build(self, docs: list[dict]) -> None:
        if not docs:
            raise ValueError("Cannot build vector index from an empty document corpus")

        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.doc_ids = [str(doc["doc_id"]) for doc in docs]
        texts = [f"{doc.get('title', '')} {doc.get('text', '')}" for doc in docs]
        embeddings = self._encode(texts)

        dimension = int(embeddings.shape[1])
        faiss = _load_faiss()
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)

        faiss.write_index(self.index, str(self.index_path))
        self.docmap_path.write_text(json.dumps(self.doc_ids, indent=2), encoding="utf-8")
        self.meta_path.write_text(
            json.dumps(
                {
                    "model_name": self.model_name,
                    "dimension": dimension,
                    "corpus_hash": self._corpus_hash(docs),
                    "build_timestamp": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def load(self) -> None:
        if not self.index_path.exists() or not self.docmap_path.exists() or not self.meta_path.exists():
            raise FileNotFoundError("Vector index artifacts are missing. Rebuild with python -m app.index")

        meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
        expected = self._model_dimension()
        actual = int(meta["dimension"])
        if expected != actual:
            raise RuntimeError(
                f"Index dimension mismatch: expected {expected}, got {actual}. Rebuild with python -m app.index"
            )

        faiss = _load_faiss()
        self.index = faiss.read_index(str(self.index_path))
        self.doc_ids = json.loads(self.docmap_path.read_text(encoding="utf-8"))

    def query(self, q: str, top_k: int) -> list[tuple[str, float]]:
        if self.index is None:
            self.load()

        query_embedding = self._encode([q])
        scores, positions = self.index.search(query_embedding, top_k)
        results: list[tuple[str, float]] = []
        for pos, score in zip(positions[0], scores[0]):
            if pos < 0:
                continue
            results.append((self.doc_ids[int(pos)], float(score)))
        return results

    def _encode(self, texts: list[str]) -> np.ndarray:
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(embeddings, dtype="float32")

    def _model_dimension(self) -> int:
        if hasattr(self.model, "get_sentence_embedding_dimension"):
            dimension = self.model.get_sentence_embedding_dimension()
            if dimension is not None:
                return int(dimension)
        return int(self._encode(["dimension probe"]).shape[1])

    @staticmethod
    def _corpus_hash(docs: list[dict]) -> str:
        payload = json.dumps(docs, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_faiss() -> Any:
    try:
        import faiss

        return faiss
    except Exception:
        return _NumpyFaissCompat


class _NumpyIndexFlatIP:
    def __init__(self, dimension: int) -> None:
        self.dimension = dimension
        self.embeddings = np.empty((0, dimension), dtype="float32")

    def add(self, embeddings: np.ndarray) -> None:
        embeddings = np.asarray(embeddings, dtype="float32")
        if embeddings.ndim != 2 or embeddings.shape[1] != self.dimension:
            raise ValueError(f"Expected embeddings with dimension {self.dimension}")
        self.embeddings = np.vstack([self.embeddings, embeddings])

    def search(self, query_embeddings: np.ndarray, top_k: int) -> tuple[np.ndarray, np.ndarray]:
        query_embeddings = np.asarray(query_embeddings, dtype="float32")
        scores = query_embeddings @ self.embeddings.T
        order = np.argsort(-scores, axis=1)[:, :top_k]
        sorted_scores = np.take_along_axis(scores, order, axis=1)
        return sorted_scores.astype("float32"), order.astype("int64")


class _NumpyFaissCompat:
    IndexFlatIP = _NumpyIndexFlatIP

    @staticmethod
    def write_index(index: _NumpyIndexFlatIP, path: str) -> None:
        with Path(path).open("wb") as handle:
            pickle.dump(index, handle)

    @staticmethod
    def read_index(path: str) -> _NumpyIndexFlatIP:
        with Path(path).open("rb") as handle:
            return pickle.load(handle)
