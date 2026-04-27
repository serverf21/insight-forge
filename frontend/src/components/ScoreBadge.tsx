import React from "react";
import type { SearchResult } from "../api/client";

interface ScoreBadgeProps {
  result: Pick<SearchResult, "bm25_score" | "vector_score" | "hybrid_score">;
}

export function ScoreBadge({ result }: ScoreBadgeProps) {
  return (
    <div className="score-badges" aria-label="Score breakdown">
      <span className="score-badge score-badge-blue">BM25 {result.bm25_score.toFixed(2)}</span>
      <span className="score-badge score-badge-green">Vector {result.vector_score.toFixed(2)}</span>
      <span className="score-badge score-badge-purple">Hybrid {result.hybrid_score.toFixed(2)}</span>
    </div>
  );
}
