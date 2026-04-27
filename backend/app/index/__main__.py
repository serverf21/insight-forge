import json
from pathlib import Path


def main() -> None:
    processed_manifest = Path("data/processed/manifest.tsv")
    bm25_dir = Path("data/index/bm25")
    vector_dir = Path("data/index/vector")
    bm25_dir.mkdir(parents=True, exist_ok=True)
    vector_dir.mkdir(parents=True, exist_ok=True)

    document_count = 0
    if processed_manifest.exists():
        document_count = max(0, len(processed_manifest.read_text(encoding="utf-8").splitlines()) - 1)

    (bm25_dir / "bm25.json").write_text(
        json.dumps({"type": "bm25", "documents": document_count}, indent=2),
        encoding="utf-8",
    )
    (vector_dir / "vector.meta.json").write_text(
        json.dumps({"type": "vector", "documents": document_count}, indent=2),
        encoding="utf-8",
    )

    print(f"Indexed {document_count} documents")


if __name__ == "__main__":
    main()
