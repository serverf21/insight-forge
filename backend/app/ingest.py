import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


SUPPORTED_EXTENSIONS = {".md", ".txt"}
MAX_WORDS = 400
TRUNCATED_SUFFIX = "[truncated]"


def discover_documents(input_dir: Path) -> Iterable[Path]:
    return sorted(
        path
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def preprocess(text: str) -> tuple[str, bool]:
    text = re.sub(r"\n\s*\n+", "\n\n", text.strip())
    words = text.split()

    if len(words) <= MAX_WORDS:
        return text, False

    return f"{' '.join(words[:MAX_WORDS])} {TRUNCATED_SUFFIX}", True


def first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def normalize_document(path: Path, input_dir: Path) -> tuple[Optional[dict[str, str]], bool]:
    raw_text = path.read_text(encoding="utf-8", errors="ignore")
    processed_text, was_truncated = preprocess(raw_text)

    if not processed_text:
        return None, False

    return (
        {
            "doc_id": hashlib.sha256(processed_text.encode("utf-8")).hexdigest()[:12],
            "title": first_non_empty_line(processed_text),
            "text": processed_text,
            "source": path.relative_to(input_dir).as_posix(),
            "created_at": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
        },
        was_truncated,
    )


def ingest(input_dir: Path, out_dir: Path) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / "docs.jsonl"

    counts = {"ingested": 0, "skipped": 0, "truncated": 0}

    with output_path.open("w", encoding="utf-8") as handle:
        for path in discover_documents(input_dir):
            record, was_truncated = normalize_document(path, input_dir)
            if record is None:
                counts["skipped"] += 1
                continue

            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            counts["ingested"] += 1
            if was_truncated:
                counts["truncated"] += 1

    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest text and markdown documents into JSONL.")
    parser.add_argument("--input", default="data/raw", type=Path, help="Input directory containing .txt/.md files.")
    parser.add_argument("--out", default="data/processed", type=Path, help="Output directory for docs.jsonl.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    counts = ingest(args.input, args.out)
    print(
        f"ingested={counts['ingested']} "
        f"skipped={counts['skipped']} "
        f"truncated={counts['truncated']}"
    )


if __name__ == "__main__":
    main()
