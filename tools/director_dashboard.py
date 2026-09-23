#!/usr/bin/env python3
"""Localhost status dashboard for the agentic director.

Serves a live page that refreshes in-browser (button + optional auto-poll).
No Cursor chat / canvas rewrite required.

  .venv/bin/python -u tools/director_dashboard.py
  open http://127.0.0.1:8765
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "logs" / "experiments.jsonl"
STATE = ROOT / "logs" / "director_state.json"
DIR_LOG = ROOT / "logs" / "director.log"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Agentic director status</title>
<style>
  :root {
    --fg: #18181b; --muted: #52525b; --border: #d4d4d8; --bg: #fafafa;
    --warn: #a16207; --bad: #b91c1c; --ok: #15803d; --card: #fff;
  }
  * { box-sizing: border-box; }
  body {
    font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
    max-width: 1100px; margin: 0 auto; padding: 1.5rem 1rem 3rem;
    color: var(--fg); line-height: 1.45; background: #fff;
  }
  h1 { font-size: 1.5rem; margin: 0; }
  h2 { font-size: 1.1rem; margin: 1.5rem 0 0.5rem; }
  .top { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center; justify-content: space-between; }
  .meta { color: var(--muted); font-size: 0.9rem; }
  button {
    appearance: none; border: 1px solid var(--fg); background: var(--fg); color: #fff;
    padding: 0.4rem 0.85rem; font: inherit; cursor: pointer; border-radius: 2px;
  }
  button.secondary { background: #fff; color: var(--fg); }
  button:disabled { opacity: 0.5; cursor: default; }
  .callout {
    border: 1px solid var(--border); background: var(--bg); padding: 0.85rem 1rem; margin: 1rem 0;
  }
  .callout.bad { border-color: #fecaca; background: #fef2f2; }
  .callout.warn { border-color: #fde68a; background: #fffbeb; }
  .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin: 1rem 0; }
  @media (max-width: 720px) { .stats { grid-template-columns: repeat(2, 1fr); } }
  .stat { border: 1px solid var(--border); padding: 0.75rem; background: var(--card); }
  .stat .v { font-size: 1.6rem; font-weight: 650; }
  .stat .l { color: var(--muted); font-size: 0.85rem; }
  .pills { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.5rem 0 1rem; }
  .pill { border: 1px solid var(--border); padding: 0.15rem 0.55rem; font-size: 0.85rem; background: var(--bg); }
  .pill.warn { color: var(--warn); border-color: #fcd34d; }
  .pill.bad { color: var(--bad); border-color: #fca5a5; }
  .pill.ok { color: var(--ok); border-color: #86efac; }
  table { border-collapse: collapse; width: 100%; font-size: 0.88rem; }
  th, td { border: 1px solid var(--border); padding: 0.35rem 0.5rem; text-align: left; vertical-align: top; }
  th { background: #f4f4f5; }
  tr.crashed td { background: #fef2f2; }
  tr.sterile td { background: #fffbeb; }
  tr.progress td { background: #ecfdf5; }
  code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.85em; }
  .err { color: var(--bad); }
</style>
</head>
<body>
  <div class="top">
    <div>
      <h1>Agentic director</h1>
      <div class="meta" id="meta">Loading…</div>
    </div>
    <div style="display:flex; gap:0.5rem; align-items:center;">
      <label class="meta"><input type="checkbox" id="auto"/> auto 30s</label>
      <button type="button" class="secondary" id="refresh">Refresh</button>
    </div>
  </div>

  <div id="banner" class="callout">Waiting for first load…</div>
  <div class="stats" id="stats"></div>
  <div class="pills" id="pills"></div>
  <h2>Hypothesis log (newest first)</h2>
  <p class="meta">
    <strong>Best</strong> = metric for that row’s arch (additions / support / rank) — lower is better;
    thresholds are &lt;56 / &lt;152 / &lt;23.
    <strong>Wall min</strong> = how long that cycle ran (minutes), not the metric.
  </p>
  <div id="table"></div>
  <p class="meta" style="margin-top:1.5rem">
    Data from <code>logs/director_state.json</code> + <code>logs/experiments.jsonl</code>.
    Overnight: <code>bash tools/resume_overnight.sh</code>
  </p>
<script>
const AUTO_MS = 30000;
let timer = null;
let lastFetchedAt = null;

function age(ms) {
  if (ms == null || ms < 0) ms = 0;
  const s = Math.floor(ms / 1000);
  if (s < 60) return s + "s ago";
  const m = Math.floor(s / 60);
  if (m < 60) return m + " min ago";
  const h = Math.floor(m / 60);
  const rem = m % 60;
  return rem ? (h + "h " + rem + "m ago") : (h + "h ago");
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  }[c]));
}

function render(data) {
  const live = data.live || {};
  const best = data.best || {};
  const totals = data.totals || {};
  const cycles = data.cycles || [];
  lastFetchedAt = Date.now();
  const snapAge = Date.now() - (data.generated_at_ms || Date.now());

  document.getElementById("meta").textContent =
    "Last updated " + age(0) + " · snapshot " + (data.generated_at_iso || "") +
    " · server clock lag " + age(snapAge);

  const alive = !!live.alive;
  const banner = document.getElementById("banner");
  banner.className = "callout " + (alive ? "" : "bad");
  banner.innerHTML = alive
    ? ("<strong>Running</strong> · cycle " + esc(live.cycle) +
       " · phase=" + esc(live.phase) +
       " · budget=" + esc(live.budget_mode) +
       " · timeout " + esc(live.timeout_s) + "s" +
       " · agent <code>" + esc(live.agent_id) + "</code>" +
       " · run <code>" + esc(live.run_id) + "</code>")
    : ("<strong>Director not running</strong> · last cycle " + esc(live.cycle) +
       " phase=" + esc(live.phase) +
       ". Start with <code>bash tools/resume_overnight.sh</code>");

  document.getElementById("stats").innerHTML = [
    ["Adds", best.additions, "target ≤55"],
    ["Support", best.support, "target ≤151"],
    ["Rank", best.rank, "target ≤22"],
    ["Sterile", (totals.sterile || 0) + "/" + (totals.n || 0), "finished cycles"],
  ].map(([l,v,s]) =>
    `<div class="stat"><div class="v">${esc(v)}</div><div class="l">${esc(l)} · ${esc(s)}</div></div>`
  ).join("");

  document.getElementById("pills").innerHTML =
    `<span class="pill warn">${esc(totals.sterile||0)} sterile</span>` +
    `<span class="pill bad">${esc(totals.crashed||0)} crashed</span>` +
    `<span class="pill ${totals.progress ? "ok" : ""}">${esc(totals.progress||0)} progress</span>` +
    (totals.avg_sterile_min != null
      ? `<span class="pill">avg sterile ≈ ${esc(totals.avg_sterile_min)} min</span>` : "");

  const rows = [...cycles].reverse().map(c => {
    const cls = esc(c.label);
    return `<tr class="${cls}"><td>${esc(c.cycle)}</td><td>${esc(c.label)}</td>` +
      `<td>${esc(c.arch)}</td><td>${c.best==null?"—":esc(c.best)}</td>` +
      `<td>${c.min==null?"—":esc(c.min)}</td><td>${esc(c.hyp)}</td></tr>`;
  }).join("");
  document.getElementById("table").innerHTML =
    `<table><thead><tr><th>Cycle</th><th>Result</th><th>Arch</th><th>Best</th><th>Wall min</th><th>Hypothesis</th></tr></thead>` +
    `<tbody>${rows || "<tr><td colspan=6>No agentic ledger rows yet</td></tr>"}</tbody></table>`;
}

function tickAge() {
  if (lastFetchedAt == null) return;
  const el = document.getElementById("meta");
  if (!el || !el.dataset.iso) return;
}

async function load() {
  const btn = document.getElementById("refresh");
  btn.disabled = true;
  try {
    const r = await fetch("/api/status?t=" + Date.now(), { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    const data = await r.json();
    render(data);
    document.getElementById("meta").dataset.iso = data.generated_at_iso || "";
  } catch (e) {
    document.getElementById("banner").className = "callout bad";
    document.getElementById("banner").innerHTML =
      "<strong class='err'>Refresh failed</strong>: " + esc(e.message);
  } finally {
    btn.disabled = false;
  }
}

function schedule() {
  if (timer) clearInterval(timer);
  timer = null;
  if (document.getElementById("auto").checked) {
    timer = setInterval(load, AUTO_MS);
  }
}

document.getElementById("refresh").addEventListener("click", load);
document.getElementById("auto").addEventListener("change", schedule);
// Keep "X ago" fresh without refetch
setInterval(() => {
  if (lastFetchedAt == null) return;
  const iso = document.getElementById("meta").dataset.iso || "";
  document.getElementById("meta").textContent =
    "Last updated " + age(Date.now() - lastFetchedAt) +
    (iso ? (" · snapshot " + iso) : "");
}, 5000);

load();
schedule();
</script>
</body>
</html>
"""


def director_alive() -> bool:
    try:
        r = subprocess.run(
            ["pgrep", "-f", "tools/agentic_director.py"],
            capture_output=True,
            text=True,
        )
        return r.returncode == 0 and bool(r.stdout.strip())
    except Exception:
        return False


def load_state() -> dict:
    if not STATE.exists():
        return {"best": {"additions": 56, "support": 152, "rank": 23}, "cycle": 0, "phase": "idle"}
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"best": {"additions": 56, "support": 152, "rank": 23}, "cycle": 0, "phase": "unknown"}


def load_agentic_rows() -> list[dict]:
    if not LEDGER.exists():
        return []
    rows = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("strategy_id") == "agentic" or r.get("director") == "agentic":
            rows.append(r)
    return rows


def build_status() -> dict:
    st = load_state()
    rows = load_agentic_rows()
    by: dict[int, dict] = {}
    for r in rows:
        c = r.get("cycle")
        if c is None or (isinstance(c, int) and c >= 100):
            continue
        elapsed = r.get("elapsed_s")
        mins = round(float(elapsed) / 60.0, 1) if isinstance(elapsed, (int, float)) else None
        hyp = (
            r.get("hypothesis")
            or r.get("missing")
            or r.get("postmortem")
            or r.get("error")
            or ""
        )
        by[int(c)] = {
            "cycle": int(c),
            "label": r.get("label")
            or ("crashed" if r.get("timed_out") else "unknown"),
            "arch": r.get("arch") or "unknown",
            "best": r.get("best"),
            "min": mins,
            "hyp": str(hyp)[:120],
        }
    cycles = sorted(by.values(), key=lambda x: x["cycle"])
    # Prefer overnight agentic range
    cycles = [c for c in cycles if c["cycle"] >= 30]
    sterile = [c for c in cycles if c["label"] == "sterile"]
    sterile_mins = [c["min"] for c in sterile if isinstance(c.get("min"), (int, float))]
    avg = round(sum(sterile_mins) / len(sterile_mins), 1) if sterile_mins else None
    agent = st.get("agent_id") or ""
    run = st.get("run_id") or ""
    now = time.time()
    return {
        "generated_at_ms": int(now * 1000),
        "generated_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "best": st.get("best") or {"additions": 56, "support": 152, "rank": 23},
        "live": {
            "alive": director_alive(),
            "cycle": st.get("cycle"),
            "phase": st.get("phase"),
            "budget_mode": st.get("budget_mode"),
            "timeout_s": 3600,
            "agent_id": (agent[:28] + "…") if len(agent) > 28 else agent,
            "run_id": (run[:24] + "…") if len(run) > 24 else run,
            "crashed_hint": st.get("crashed_hint"),
        },
        "totals": {
            "n": len(cycles),
            "sterile": len(sterile),
            "crashed": sum(1 for c in cycles if c["label"] == "crashed"),
            "progress": sum(1 for c in cycles if c["label"] == "progress"),
            "avg_sterile_min": avg,
        },
        "cycles": cycles,
        "log_tail": _tail_log(8),
    }


def _tail_log(n: int) -> list[str]:
    if not DIR_LOG.exists():
        return []
    lines = DIR_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-n:]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        # Quiet: only API errors matter for overnight
        if self.path.startswith("/api/"):
            return

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path == "/api/status":
            try:
                payload = json.dumps(build_status()).encode("utf-8")
                self._send(200, payload, "application/json; charset=utf-8")
            except Exception as e:
                err = json.dumps({"error": str(e)}).encode("utf-8")
                self._send(500, err, "application/json; charset=utf-8")
            return
        self._send(404, b'{"error":"not found"}', "application/json; charset=utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Local agentic director status dashboard")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = ap.parse_args()
    os.chdir(ROOT)
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(
        f"director dashboard http://{args.host}:{args.port}/  (Ctrl-C to stop)",
        flush=True,
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
