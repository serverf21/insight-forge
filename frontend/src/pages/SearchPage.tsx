import React, { useEffect, useMemo, useState } from "react";
import { searchDocuments, type SearchResponse } from "../api/client";
import { ScoreBadge } from "../components/ScoreBadge";

const TOP_K_OPTIONS = [5, 10, 20];

export function SearchPage() {
  const [query, setQuery] = useState("Alan Turing computer science");
  const [debouncedQuery, setDebouncedQuery] = useState(query);
  const [alpha, setAlpha] = useState(0.5);
  const [topK, setTopK] = useState(10);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const hasQuery = debouncedQuery.trim().length > 0;

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query), 300);
    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    if (!hasQuery) {
      setResponse(null);
      setError("");
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    setError("");

    searchDocuments({ query: debouncedQuery.trim(), top_k: topK, alpha })
      .then((nextResponse) => {
        if (!controller.signal.aborted) {
          setResponse(nextResponse);
        }
      })
      .catch((err: Error) => {
        if (!controller.signal.aborted) {
          setError(err.message);
          setResponse(null);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [alpha, debouncedQuery, hasQuery, topK]);

  const resultCountLabel = useMemo(() => {
    if (!response) return "No query submitted";
    return `${response.total} result${response.total === 1 ? "" : "s"}`;
  }, [response]);

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Search</h1>
          <p>Blend lexical and vector search over the indexed Wikipedia sample.</p>
        </div>
        <div className="status-pill">{resultCountLabel}</div>
      </div>

      <div className="toolbar">
        <label className="field field-grow">
          <span>Query</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search the corpus"
            maxLength={500}
          />
        </label>

        <label className="field slider-field">
          <span>Alpha {alpha.toFixed(1)}</span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={alpha}
            onChange={(event) => setAlpha(Number(event.target.value))}
          />
        </label>

        <label className="field select-field">
          <span>Top K</span>
          <select value={topK} onChange={(event) => setTopK(Number(event.target.value))}>
            {TOP_K_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="result-meta">
        {loading ? "Searching..." : response ? `Latency ${response.latency_ms.toFixed(1)} ms` : "Ready"}
      </div>

      {error && <div className="notice notice-error">{error}</div>}
      {!loading && !error && hasQuery && response?.results.length === 0 && (
        <div className="empty-state">No results found</div>
      )}

      <div className="results-list">
        {response?.results.map((result) => (
          <article className="result-item" key={result.doc_id}>
            <div className="result-main">
              <h2>{result.title || result.doc_id}</h2>
              <p>{result.snippet.slice(0, 200)}</p>
            </div>
            <ScoreBadge result={result} />
          </article>
        ))}
      </div>
    </section>
  );
}
