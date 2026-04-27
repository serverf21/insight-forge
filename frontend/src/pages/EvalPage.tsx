import React, { useEffect, useMemo, useState } from "react";
import { getExperiments, type ExperimentRun } from "../api/client";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface ExperimentPoint extends ExperimentRun {
  run: number;
  ndcgValue: number;
  recallValue: number;
  mrrValue: number;
  isBest: boolean;
}

export function EvalPage() {
  const [experiments, setExperiments] = useState<ExperimentRun[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    getExperiments()
      .then((rows) => {
        if (!cancelled) {
          setExperiments(rows);
          setError("");
        }
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const sorted = useMemo(
    () => [...experiments].sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp)),
    [experiments],
  );

  const chartData = useMemo(() => {
    const chronological = [...experiments].sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
    const bestNdcg = Math.max(...chronological.map((run) => Number(run.ndcg10)), -Infinity);
    return chronological.map((run, index): ExperimentPoint => {
      const ndcgValue = Number(run.ndcg10);
      return {
        ...run,
        run: index + 1,
        ndcgValue,
        recallValue: Number(run.recall10),
        mrrValue: Number(run.mrr10),
        isBest: ndcgValue === bestNdcg,
      };
    });
  }, [experiments]);

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Experiments</h1>
          <p>Evaluation runs from the hybrid search benchmark.</p>
        </div>
        <div className="status-pill">{experiments.length} runs</div>
      </div>

      {error && <div className="notice notice-error">{error}</div>}

      {experiments.length === 0 ? (
        <div className="empty-state">No experiments yet</div>
      ) : (
        <>
          <section className="panel">
            <h2>nDCG@10 Trend</h2>
            <div className="chart-box">
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="run" tick={{ fontSize: 12 }} />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="ndcgValue"
                    name="nDCG@10"
                    stroke="var(--purple)"
                    strokeWidth={2}
                    dot={(props) => {
                      const point = chartData[props.index ?? -1];
                      return (
                        <circle
                          cx={props.cx}
                          cy={props.cy}
                          r={point?.isBest ? 6 : 4}
                          fill={point?.isBest ? "var(--green)" : "var(--purple)"}
                          stroke="#fff"
                          strokeWidth={2}
                        />
                      );
                    }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section className="panel">
            <h2>Experiment Runs</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Alpha</th>
                    <th>Model</th>
                    <th>nDCG@10</th>
                    <th>Recall@10</th>
                    <th>MRR@10</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((run) => {
                    const isBest = Number(run.ndcg10) === Math.max(...experiments.map((item) => Number(item.ndcg10)));
                    return (
                      <tr className={isBest ? "row-success" : ""} key={`${run.timestamp}-${run.alpha}`}>
                        <td>{formatDate(run.timestamp)}</td>
                        <td>{Number(run.alpha).toFixed(1)}</td>
                        <td>{run.model}</td>
                        <td>{Number(run.ndcg10).toFixed(3)}</td>
                        <td>{Number(run.recall10).toFixed(3)}</td>
                        <td>{Number(run.mrr10).toFixed(3)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </section>
  );
}

function formatDate(value: string) {
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return value;
  return new Date(timestamp).toLocaleString();
}
