import { useEffect, useState } from "react";
import {
  fetchSystemStatus,
  type OverallState,
  type SystemStatus,
} from "../api/status";
import "./StatusPage.css";

const INITIAL: SystemStatus = {
  overall: "loading",
  apiLive: "unknown",
  database: "unknown",
  detail: "Checking system status…",
};

function labelFor(state: OverallState): string {
  switch (state) {
    case "loading":
      return "Loading";
    case "healthy":
      return "Healthy";
    case "degraded":
      return "Degraded";
    case "unavailable":
      return "Unavailable";
  }
}

export interface StatusPageProps {
  fetcher?: typeof fetchSystemStatus;
}

export function StatusPage({ fetcher = fetchSystemStatus }: StatusPageProps) {
  const [status, setStatus] = useState<SystemStatus>(INITIAL);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const next = await fetcher();
      if (!cancelled) {
        setStatus(next);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [fetcher]);

  return (
    <main className="status-page" data-testid="status-page">
      <header className="status-header">
        <p className="eyebrow">Zorqen</p>
        <h1>Zorqen Research</h1>
        <p className="lede">
          Autonomous strategy research and qualification system. This application
          evaluates candidates offline; it does not execute trades.
        </p>
      </header>

      <section
        className={`status-panel state-${status.overall}`}
        aria-live="polite"
        data-testid="status-panel"
        data-state={status.overall}
      >
        <h2>System status: {labelFor(status.overall)}</h2>
        <p className="detail" data-testid="status-detail">
          {status.detail}
        </p>
        <dl className="status-grid">
          <div>
            <dt>API liveness</dt>
            <dd data-testid="api-live-status">{status.apiLive}</dd>
          </div>
          <div>
            <dt>Database readiness</dt>
            <dd data-testid="database-status">{status.database}</dd>
          </div>
        </dl>
      </section>

      <p className="boundary">
        Trading execution, exchange connectivity, paper trading, and live order
        placement are outside this application and belong to MOMO Quant.
      </p>
    </main>
  );
}
