# Decision Log

## Min-Max vs Softmax Normalization

Hybrid search uses min-max normalization by default because it maps BM25 and vector scores into the same bounded 0.0–1.0 range while preserving per-query rank order. This is easier to inspect and tune than softmax, whose output can become overly peaked when one retrieval family has a wider score spread. The equal-score fallback returns a uniform distribution, giving predictable finite behavior when candidate scores tie.

## all-MiniLM-L6-v2 Over Larger Models

The vector index uses `all-MiniLM-L6-v2` because its 384-dimensional embeddings keep FAISS artifacts small and CPU inference practical for a local dashboard workflow. It provides enough semantic quality for a 300-document Wikipedia sample and leaves room to scale toward thousands of documents without turning every query into a slow model call. Larger models such as MPNet can improve quality, but they double dimensionality and increase startup/query cost for little benefit at this corpus size.

## SQLite Over Postgres

SQLite is the right operational fit for this single-node eval pipeline because it is zero-ops, file-backed, and ships naturally with the repo workflow. The query log, metrics, and experiment records are local observability data rather than high-concurrency transactional state. A forward-only migration helper is enough here, while Postgres would add deployment and credential complexity before the system needs it.

## FAISS IndexFlatIP Over HNSW

`IndexFlatIP` gives exact inner-product search, which is acceptable for the current target of fewer than 10k documents. Exact search avoids recall tradeoffs, graph tuning parameters, and harder-to-explain evaluation differences. Rebuild logic is also simpler: encode the corpus, normalize embeddings, write one flat index and metadata.
