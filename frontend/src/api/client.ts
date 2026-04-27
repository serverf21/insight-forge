export interface SearchResult {
  doc_id: string;
  title: string;
  snippet: string;
  bm25_score: number;
  vector_score: number;
  hybrid_score: number;
}

export interface SearchRequest {
  query: string;
  top_k?: number;
  alpha?: number;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  latency_ms: number;
}

export interface MetricsSnapshot {
  search_requests_total: number;
  search_zero_results_total: number;
  search_latency_p50_ms: number;
  search_latency_p95_ms: number;
}

export interface QueryLog {
  id: number;
  request_id: string;
  query: string;
  alpha: number;
  top_k: number;
  result_count: number;
  latency_ms: number;
  error: string;
  created_at: string | null;
}

export interface LogsResponse {
  total: number;
  items: QueryLog[];
}

export async function searchDocuments(payload: SearchRequest): Promise<SearchResponse> {
  const response = await fetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJsonResponse<SearchResponse>(response);
}

export async function getMetrics(): Promise<MetricsSnapshot> {
  const response = await fetch("/api/metrics");
  if (!response.ok) {
    throw new Error(`GET /metrics failed with ${response.status}`);
  }
  return parsePrometheusMetrics(await response.text());
}

export async function getLogs(limit = 1000): Promise<LogsResponse> {
  const response = await fetch(`/api/logs?limit=${limit}`);
  return parseJsonResponse<LogsResponse>(response);
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function parsePrometheusMetrics(text: string): MetricsSnapshot {
  const snapshot: MetricsSnapshot = {
    search_requests_total: 0,
    search_zero_results_total: 0,
    search_latency_p50_ms: 0,
    search_latency_p95_ms: 0,
  };

  for (const line of text.split("\n")) {
    const [name, rawValue] = line.trim().split(/\s+/);
    if (name in snapshot) {
      snapshot[name as keyof MetricsSnapshot] = Number(rawValue);
    }
  }

  return snapshot;
}
