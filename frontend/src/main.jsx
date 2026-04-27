import React from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

function App() {
  return (
    <main className="app">
      <section className="shell">
        <h1>Insight Forge</h1>
        <p>Hybrid search and KPI dashboard scaffold.</p>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
