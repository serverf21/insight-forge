import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingest import ingest


def read_jsonl(path: Path) -> list[dict[str, str]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_three_file_input_produces_jsonl_records_with_expected_fields(tmp_path):
    input_dir = tmp_path / "raw"
    out_dir = tmp_path / "processed"
    nested_dir = input_dir / "nested"
    nested_dir.mkdir(parents=True)

    (input_dir / "alpha.txt").write_text("Alpha Title\n\nAlpha body", encoding="utf-8")
    (input_dir / "beta.md").write_text("\n\nBeta Title\nBeta body", encoding="utf-8")
    (nested_dir / "gamma.txt").write_text("Gamma Title\n\nGamma body", encoding="utf-8")

    counts = ingest(input_dir, out_dir)
    records = read_jsonl(out_dir / "docs.jsonl")

    assert counts == {"ingested": 3, "skipped": 0, "truncated": 0}
    assert len(records) == 3
    assert {record["title"] for record in records} == {"Alpha Title", "Beta Title", "Gamma Title"}
    assert {record["source"] for record in records} == {
        "alpha.txt",
        "beta.md",
        "nested/gamma.txt",
    }

    for record in records:
        assert set(record) == {"doc_id", "title", "text", "source", "created_at"}
        assert len(record["doc_id"]) == 12
        assert record["created_at"].endswith("+00:00")
        assert record["text"].strip() == record["text"]


def test_document_over_400_words_is_truncated(tmp_path):
    input_dir = tmp_path / "raw"
    out_dir = tmp_path / "processed"
    input_dir.mkdir()

    (input_dir / "long.txt").write_text(" ".join(f"word{i}" for i in range(405)), encoding="utf-8")

    counts = ingest(input_dir, out_dir)
    [record] = read_jsonl(out_dir / "docs.jsonl")

    assert counts == {"ingested": 1, "skipped": 0, "truncated": 1}
    assert record["text"].endswith("[truncated]")
    assert len(record["text"].removesuffix(" [truncated]").split()) == 400


def test_empty_file_is_skipped_and_counted(tmp_path):
    input_dir = tmp_path / "raw"
    out_dir = tmp_path / "processed"
    input_dir.mkdir()

    (input_dir / "empty.txt").write_text(" \n\n\t ", encoding="utf-8")
    (input_dir / "keep.md").write_text("Keep\n\nBody", encoding="utf-8")

    counts = ingest(input_dir, out_dir)
    records = read_jsonl(out_dir / "docs.jsonl")

    assert counts == {"ingested": 1, "skipped": 1, "truncated": 0}
    assert len(records) == 1
    assert records[0]["source"] == "keep.md"
