import React from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { KpiPage } from "./pages/KpiPage";
import { SearchPage } from "./pages/SearchPage";

function PlaceholderPage({ title }: { title: string }) {
  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>{title}</h1>
          <p>This workspace is ready for the next workflow.</p>
        </div>
      </div>
      <div className="panel">
        <div className="empty-state compact">No records loaded yet</div>
      </div>
    </section>
  );
}

export function App() {
  return (
    <div className="app-shell">
      <nav className="nav">
        <div className="brand">Insight Forge</div>
        <div className="nav-links">
          <NavLink to="/search">Search</NavLink>
          <NavLink to="/kpis">KPIs</NavLink>
          <NavLink to="/experiments">Experiments</NavLink>
          <NavLink to="/logs">Logs</NavLink>
        </div>
      </nav>
      <main className="content">
        <Routes>
          <Route path="/" element={<Navigate to="/search" replace />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/kpis" element={<KpiPage />} />
          <Route path="/experiments" element={<PlaceholderPage title="Experiments" />} />
          <Route path="/logs" element={<PlaceholderPage title="Logs" />} />
        </Routes>
      </main>
    </div>
  );
}
