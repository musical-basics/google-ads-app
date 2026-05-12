"use client";
import { useState } from "react";

type Status = { exists: boolean; state: any; live: any; live_error?: string | null };

export default function Page() {
  const [apiKey, setApiKey] = useState("");
  const [status, setStatus] = useState<Status | null>(null);
  const [summary, setSummary] = useState<string>("");
  const [prereqs, setPrereqs] = useState<any>(null);
  const [err, setErr] = useState<string>("");

  async function call(path: string) {
    setErr("");
    const r = await fetch(path, { headers: { Authorization: `Bearer ${apiKey}` } });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) {
      setErr(`${r.status} ${path}: ${body.error || r.statusText}`);
      return null;
    }
    return body;
  }

  async function refresh() {
    const p = await call("/api/prereqs/check");
    if (p) setPrereqs(p);
    const s = await call("/api/campaign/status");
    if (s) setStatus(s);
    const d = await call("/api/summary/daily");
    if (d) setSummary(d.text);
  }

  return (
    <main>
      <h1>Belgium concert ads - status</h1>
      <p className="muted">Read-only dashboard. All mutations happen through your AI agent.</p>

      <h2>Auth</h2>
      <div style={{ display: "flex", gap: 8 }}>
        <input className="input" placeholder="API key" type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
        <button className="btn" onClick={refresh} disabled={!apiKey}>Refresh</button>
      </div>
      {err && <p className="err" style={{ marginTop: 12 }}>{err}</p>}

      {prereqs && (
        <>
          <h2>Prereqs</h2>
          <div className="row">
            <span>Overall</span>
            <span className={prereqs.ok ? "ok" : "err"}>{prereqs.ok ? "ready" : "blocked"}</span>
          </div>
          {prereqs.blockers?.map((b: any) => (
            <div className="row" key={b.key}>
              <span className="err">{b.key}</span>
              <span className="muted" style={{ textAlign: "right", maxWidth: "60%" }}>{b.message}</span>
            </div>
          ))}
        </>
      )}

      {status && (
        <>
          <h2>Campaign</h2>
          <div className="row"><span>Exists</span><span>{status.exists ? "yes" : "no"}</span></div>
          {status.state && (
            <>
              <div className="row"><span>Status</span><span>{status.state.status}</span></div>
              <div className="row"><span>Daily budget</span><span>{((status.state.daily_budget_cents || 0) / 100).toFixed(2)} EUR</span></div>
              <div className="row"><span>Total budget</span><span>{((status.state.total_budget_cents || 0) / 100).toFixed(2)} EUR</span></div>
              <div className="row"><span>Spend to date</span><span>{((status.state.spend_to_date_cents || 0) / 100).toFixed(2)} EUR</span></div>
              <div className="row"><span>Conversions</span><span>{status.state.conversions_to_date || 0}</span></div>
            </>
          )}
        </>
      )}

      {summary && (
        <>
          <h2>Latest summary</h2>
          <pre>{summary}</pre>
        </>
      )}
    </main>
  );
}
