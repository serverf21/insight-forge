import React, { useEffect, useMemo, useState } from "react";
import {
  getLogs,
  getMetrics,
  type MetricsSnapshot,
  type QueryLog,
} from "../api/client";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface TimedSnapshot extends MetricsSnapshot {
  label: string;
}

export function KpiPage() {
  const [snapshots, setSnapshots] = useState<TimedSnapshot[]>([]);
  const [logs, setLogs] = useState<QueryLog[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function refresh() {
      try {
        const [metrics, logResponse] = await Promise.all([getMetrics(), getLogs(1000)]);
        if (cancelled) return;
        const label = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
        setSnapshots((current) => [...current, { ...metrics, label }].slice(-20));
        setLogs(logResponse.items);
        setError("");
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load metrics");
        }
      }
    }

    refresh();
    const timer = window.setInterval(refresh, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const latest = snapshots[snapshots.length - 1];
  const topQueries = useMemo(() => rankQueries(logs, false), [logs]);
  const zeroResultQueries = useMemo(() => rankQueries(logs, true), [logs]);

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>KPI Dashboard</h1>
          <p>Operational search metrics from the backend query log.</p>
        </div>
        <div className="status-pill">Refreshes every 30s</div>
      </div>

      {error && <div className="notice notice-error">{error}</div>}

      <div className="stats-grid">
        <StatCard label="P50 Latency" value={`${(latest?.search_latency_p50_ms ?? 0).toFixed(1)} ms`} />
        <StatCard label="P95 Latency" value={`${(latest?.search_latency_p95_ms ?? 0).toFixed(1)} ms`} />
        <StatCard label="Requests" value={`${latest?.search_requests_total ?? 0}`} />
        <StatCard label="Zero Results" value={`${latest?.search_zero_results_total ?? 0}`} />
      </div>

      <section className="panel">
        <h2>Request Volume</h2>
        <div className="chart-box">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={snapshots}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={18} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="search_requests_total"
                name="Requests"
                stroke="var(--blue)"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <div className="ranked-grid">
        <RankedList title="Top Queries" items={topQueries} />
        <RankedList title="Zero-Result Queries" items={zeroResultQueries} />
      </div>
    </section>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function RankedList({ title, items }: { title: string; items: Array<{ query: string; count: number }> }) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      {items.length === 0 ? (
        <div className="empty-state compact">No data yet</div>
      ) : (
        <ol className="ranked-list">
          {items.map((item) => (
            <li key={item.query}>
              <span>{item.query}</span>
              <strong>{item.count}</strong>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function rankQueries(logs: QueryLog[], zeroOnly: boolean) {
  const counts = new Map<string, number>();
  for (const log of logs) {
    if (zeroOnly && log.result_count !== 0) continue;
    counts.set(log.query, (counts.get(log.query) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([query, count]) => ({ query, count }))
    .sort((a, b) => b.count - a.count || a.query.localeCompare(b.query))
    .slice(0, 8);
}
