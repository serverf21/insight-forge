## Hybrid Score Normalization

Default hybrid search uses min-max normalization before combining BM25 and vector scores. BM25 raw scores and vector inner-product scores live on different scales, so min-max keeps the blend interpretable for each query while preserving within-query rank order. When all scores are equal, normalization returns a uniform distribution to avoid divide-by-zero and to make ties explicit.
