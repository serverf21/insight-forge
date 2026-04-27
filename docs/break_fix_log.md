# Break/Fix Log

## Scenario A — Index Dimension Mismatch

### Injection

Simulated a startup configuration drift where the vector searcher uses a 768-dimensional encoder (`all-mpnet-base-v2`) while the saved FAISS metadata still records the existing `all-MiniLM-L6-v2` 384-dimensional index. The permanent regression test uses a fixed 768-dimensional model double to avoid network/model download during CI, but it exercises the same `VectorIndex.load()` validation path that a temporary `vector.py` model-name patch would hit.

Command evidence:

```bash
PYTHONPATH="$PWD/backend" .venv/bin/python - <<'PY'
from pathlib import Path
from app.search.vector import VectorIndex

class FixedDimModel:
    def get_sentence_embedding_dimension(self):
        return 768

index_dir = Path('/tmp/if_vector_mismatch')
index_dir.mkdir(exist_ok=True)
(index_dir / 'index.faiss').write_bytes(b'placeholder')
(index_dir / 'docmap.json').write_text('["doc-1"]', encoding='utf-8')
(index_dir / 'meta.json').write_text('{"dimension": 384}', encoding='utf-8')
try:
    VectorIndex(index_dir=index_dir, model=FixedDimModel()).load()
except RuntimeError as exc:
    print(type(exc).__name__ + ': ' + str(exc))
PY
```

### Observed failure

```text
RuntimeError: Index dimension mismatch: expected 768, got 384. Rebuild with python -m app.index
```

### Root cause

The vector index artifacts are model-specific. A 384-dimensional FAISS `IndexFlatIP` built with `all-MiniLM-L6-v2` cannot safely serve queries encoded with a 768-dimensional model such as `all-mpnet-base-v2`.

### Fix applied

`VectorIndex.load()` validates `meta.json` dimension against the current model output dimension before reading/searching the FAISS index. If the dimensions differ, startup fails fast with an explicit rebuild instruction.

### Verification

Permanent regression coverage:

```bash
.venv/bin/python -m pytest backend/tests/test_regressions.py::test_vector_dimension_mismatch_raises_rebuild_message -q
```

Result:

```text
1 passed
```

## Scenario B — SQLite Schema Migration

### Injection

Created a `query_logs` table with `user_agent TEXT NOT NULL` and no default, then attempted to insert a normal query log row without providing `user_agent`.

Command evidence:

```bash
PYTHONPATH="$PWD/backend" .venv/bin/python - <<'PY'
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from app.db.session import init_db

path = Path('/tmp/if_bad_schema.db')
path.unlink(missing_ok=True)
engine = create_engine(f'sqlite:///{path}', connect_args={'check_same_thread': False})
with engine.begin() as c:
    c.execute(text('''CREATE TABLE query_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id VARCHAR(64) NOT NULL,
        query TEXT NOT NULL,
        alpha FLOAT NOT NULL DEFAULT 0.5,
        top_k INTEGER NOT NULL DEFAULT 10,
        result_count INTEGER NOT NULL DEFAULT 0,
        latency_ms FLOAT NOT NULL DEFAULT 0.0,
        error TEXT NOT NULL DEFAULT '',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        user_agent TEXT NOT NULL
    )'''))
    try:
        c.execute(text("""INSERT INTO query_logs
            (request_id, query, alpha, top_k, result_count, latency_ms, error, created_at)
            VALUES ('before', 'q', 0.5, 10, 0, 1.0, '', CURRENT_TIMESTAMP)"""))
    except IntegrityError as exc:
        print('before:', exc.orig)
init_db(engine)
with engine.begin() as c:
    c.execute(text("""INSERT INTO query_logs
        (request_id, query, alpha, top_k, result_count, latency_ms, error, created_at)
        VALUES ('after', 'q', 0.5, 10, 1, 2.0, '', CURRENT_TIMESTAMP)"""))
    print('after:', c.execute(text("SELECT user_agent FROM query_logs WHERE request_id='after'")).scalar_one())
PY
```

### Observed failure

```text
before: NOT NULL constraint failed: query_logs.user_agent
```

### Root cause

SQLite accepted a hand-created `NOT NULL` column without a default. Normal `/search` logging inserts did not include `user_agent`, so inserts failed before the query log row could be committed.

### Fix applied

`backend/app/db/session.py` now treats schema version `3` as current and includes `user_agent TEXT NOT NULL DEFAULT 'unknown'` in the forward migration. It also detects the broken existing state where `user_agent` is present but has no default, rebuilds `query_logs` once, copies existing rows, and fills `user_agent` with `'unknown'`. `QueryLog` metadata now includes `user_agent` with a server default so recreated tables keep the default.

### Verification

After applying the migration repair:

```text
after: unknown
```

Permanent regression coverage:

```bash
.venv/bin/python -m pytest backend/tests/test_regressions.py::test_sqlite_migration_repairs_user_agent_without_default -q
```

Result:

```text
1 passed
```

## Scenario C — Normalization Divide-by-Zero Regression

### Injection

Temporarily disabled the equal-score guard in `minmax_normalize()`:

```python
if False and math.isclose(minimum, maximum):
    return [1.0 / len(scores)] * len(scores)
```

Then ran a regression test with three identical BM25 scores.

Command evidence:

```bash
.venv/bin/python -m pytest backend/tests/test_regressions.py::test_hybrid_equal_scores_do_not_emit_nan -q
```

### Observed failure

```text
ZeroDivisionError: float division by zero
```

The failure occurred at:

```text
backend/app/search/hybrid.py:36: in minmax_normalize
return [(score - minimum) / span for score in scores]
```

### Root cause

When all scores are identical, min and max are equal, so the min-max span is zero. Dividing by zero either raises immediately or can produce invalid floating-point values in other implementations.

### Fix applied

Restored the equal-score guard:

```python
if math.isclose(minimum, maximum):
    return [1.0 / len(scores)] * len(scores)
```

This gives tied candidates a finite uniform normalized weight and avoids divide-by-zero.

### Verification

Permanent regression coverage:

```bash
.venv/bin/python -m pytest backend/tests/test_regressions.py::test_hybrid_equal_scores_do_not_emit_nan -q
```

Result after restoring the guard:

```text
1 passed
```

Full backend suite after all fixes:

```bash
.venv/bin/python -m pytest backend/tests
```

Result:

```text
23 passed, 1 warning
```
