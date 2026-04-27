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

export interface ExperimentRun {
  timestamp: string;
  alpha: string;
  model: string;
  preprocessing?: string;
  ndcg10: string;
  recall10: string;
  mrr10: string;
}

export interface LogFilters {
  severity?: "error" | "info";
  from_ts?: string;
  to_ts?: string;
  limit?: number;
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

export async function getLogs(limitOrFilters: number | LogFilters = 1000): Promise<LogsResponse> {
  const filters: LogFilters =
    typeof limitOrFilters === "number" ? { limit: limitOrFilters } : limitOrFilters;
  const params = new URLSearchParams();
  params.set("limit", String(filters.limit ?? 1000));
  if (filters.severity) params.set("severity", filters.severity);
  if (filters.from_ts) params.set("from_ts", filters.from_ts);
  if (filters.to_ts) params.set("to_ts", filters.to_ts);
  const response = await fetch(`/api/logs?${params.toString()}`);
  return parseJsonResponse<LogsResponse>(response);
}

export async function getExperiments(): Promise<ExperimentRun[]> {
  const response = await fetch("/api/experiments");
  return parseJsonResponse<ExperimentRun[]>(response);
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
