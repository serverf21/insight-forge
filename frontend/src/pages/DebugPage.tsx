import React, { useEffect, useMemo, useState } from "react";
import { getLogs, type LogFilters, type QueryLog } from "../api/client";

const PAGE_SIZE = 20;

type Severity = "ALL" | "ERROR" | "INFO";

export function DebugPage() {
  const [severity, setSeverity] = useState<Severity>("ALL");
  const [fromTs, setFromTs] = useState("");
  const [toTs, setToTs] = useState("");
  const [logs, setLogs] = useState<QueryLog[]>([]);
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    const filters: LogFilters = { limit: 1000 };
    if (severity === "ERROR") filters.severity = "error";
    if (severity === "INFO") filters.severity = "info";
    if (fromTs) filters.from_ts = new Date(fromTs).toISOString();
    if (toTs) filters.to_ts = new Date(toTs).toISOString();

    getLogs(filters)
      .then((response) => {
        if (!cancelled) {
          setLogs(response.items);
          setPage(1);
          setError("");
        }
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      });

    return () => {
      cancelled = true;
    };
  }, [fromTs, severity, toTs]);

  const totalPages = Math.max(1, Math.ceil(logs.length / PAGE_SIZE));
  const pageRows = useMemo(
    () => logs.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [logs, page],
  );

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Logs</h1>
          <p>Query log inspection with severity and date filters.</p>
        </div>
        <div className="status-pill">{logs.length} rows</div>
      </div>

      <div className="toolbar">
        <label className="field select-field">
          <span>Severity</span>
          <select value={severity} onChange={(event) => setSeverity(event.target.value as Severity)}>
            <option value="ALL">ALL</option>
            <option value="ERROR">ERROR</option>
            <option value="INFO">INFO</option>
          </select>
        </label>
        <label className="field">
          <span>From</span>
          <input type="datetime-local" value={fromTs} onChange={(event) => setFromTs(event.target.value)} />
        </label>
        <label className="field">
          <span>To</span>
          <input type="datetime-local" value={toTs} onChange={(event) => setToTs(event.target.value)} />
        </label>
      </div>

      {error && <div className="notice notice-error">{error}</div>}

      <section className="panel">
        <div className="table-header">
          <h2>Query Logs</h2>
          <div className="pager">
            <button disabled={page === 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>
              Prev
            </button>
            <span>
              Page {page} of {totalPages}
            </span>
            <button disabled={page === totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))}>
              Next
            </button>
          </div>
        </div>

        {logs.length === 0 ? (
          <div className="empty-state compact">No log rows match the current filters</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Request ID</th>
                  <th>Query</th>
                  <th>Latency</th>
                  <th>Results</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {pageRows.map((log) => (
                  <tr className={log.error ? "row-error" : ""} key={log.id}>
                    <td>{formatDate(log.created_at)}</td>
                    <td className="mono">{log.request_id}</td>
                    <td>{log.query}</td>
                    <td>{log.latency_ms.toFixed(1)} ms</td>
                    <td>{log.result_count}</td>
                    <td>{log.error || ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </section>
  );
}

function formatDate(value: string | null) {
  if (!value) return "";
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return value;
  return new Date(timestamp).toLocaleString();
}
