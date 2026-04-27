import React from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { DebugPage } from "./pages/DebugPage";
import { EvalPage } from "./pages/EvalPage";
import { KpiPage } from "./pages/KpiPage";
import { SearchPage } from "./pages/SearchPage";

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
          <Route path="/experiments" element={<EvalPage />} />
          <Route path="/logs" element={<DebugPage />} />
        </Routes>
      </main>
    </div>
  );
}
