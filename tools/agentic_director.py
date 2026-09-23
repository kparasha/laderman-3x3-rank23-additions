#!/usr/bin/env python3
"""Local Cursor Agent SDK research director for the 3×3 tensor climb.

Outer Python loop + durable local agent that improvises from the experiment
ledger (not a fixed strategies.json queue).

  .venv/bin/python -u tools/agentic_director.py --once
  .venv/bin/python -u tools/agentic_director.py --max-cycles 20 --timeout 3600 --timeout-max 5400
  bash tools/resume_overnight.sh   # caffeinate-wrapped overnight

Auth: CURSOR_API_KEY in the environment or a gitignored .env at repo root.
Requires Python >=3.10 and cursor-sdk (see requirements.txt).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "logs" / "experiments.jsonl"
STATE = ROOT / "logs" / "director_state.json"
JOURNAL = ROOT / "journal.html"
DIR_LOG = ROOT / "logs" / "director.log"
CYCLE_RESULT = ROOT / "logs" / "agent_cycle_result.json"
LEARNINGS = ROOT / "tools" / "learnings.md"
HEARTBEAT = ROOT / "logs" / "agent_heartbeat.json"

STOP = False
DEFAULT_MODEL = "composer-2.5"
DEFAULT_TIMEOUT = 3600.0
DEFAULT_TIMEOUT_MAX = 5400.0

STERILE_FACTS = """
Hard facts (do not re-run these neighborhoods with the same seeds/moves):
- Sun W nullspace dim=0 given U,V — cannot vary W alone for additions.
- Signflip + greedy W CSE always lands >=57 (improvements=0 overnight).
- UV-affine mutate+solve W: no mass at cost<=56 (scored tens of thousands).
- Stapleton 2/3-edit: accept_rate~8.5% but improved=0 over ~2M edits (plateau at 152).
- Scheme CSE Stapleton/Perminov/Laderman bottoms ~64–66 with le56=0.
- Multi-seed support stuck at 152; flipgraph/rank-drop found no exact rank<23.
Priority: additions (certified SLP <56 @ rank 23) → support <152 → rank <23.
Baselines: Sun56 adds=56, Stapleton support=152, rank=23.
""".strip()


def _on_sig(_sig, _frame):
    global STOP
    STOP = True
    log("interrupt received — stop after current cycle")


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
    print(line, flush=True)
    DIR_LOG.parent.mkdir(parents=True, exist_ok=True)
    with DIR_LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def require_api_key() -> str:
    load_dotenv()
    key = (os.environ.get("CURSOR_API_KEY") or "").strip()
    if not key:
        raise SystemExit(
            "CURSOR_API_KEY missing. Export it or put it in a gitignored .env "
            "(see .env.example). Create a key at https://cursor.com/dashboard/integrations"
        )
    return key


def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "cycle": 0,
        "phase": "idle",
        "agent_id": None,
        "run_id": None,
        "cycle_started_ts": None,
        "pending_hypothesis": None,
        "last_result_ingested_mtime": None,
        "best": {"additions": 56, "support": 152, "rank": 23},
        "crashed_hint": None,
    }


def save_state(st: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, STATE)


def append_ledger(event: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    event = {**event, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "director": "agentic"}
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def tail_ledger(n: int = 12) -> list[dict]:
    if not LEDGER.exists():
        return []
    lines = LEDGER.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines[-n:]:
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def ensure_learnings() -> None:
    if LEARNINGS.exists():
        return
    LEARNINGS.write_text(
        "# Research learnings (agentic director)\n\n"
        + STERILE_FACTS
        + "\n\n## Updates\n\n(appended by agentic_director after each cycle)\n",
        encoding="utf-8",
    )


def append_learning(note: str) -> None:
    ensure_learnings()
    with LEARNINGS.open("a", encoding="utf-8") as f:
        f.write(f"\n- {time.strftime('%Y-%m-%d %H:%M')} {note}\n")


def recent_tool_files(limit: int = 15) -> list[str]:
    tools = sorted(
        (ROOT / "tools").glob("*.py"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return [str(p.relative_to(ROOT)) for p in tools[:limit]]


def _is_timeout_row(r: dict) -> bool:
    if r.get("timed_out"):
        return True
    miss = str(r.get("missing") or "").lower()
    return miss in ("timed_out", "timed out") or "timed out" in miss


def _is_crash_row(r: dict) -> bool:
    return r.get("label") == "crashed" or _is_timeout_row(r)


def read_heartbeat() -> dict | None:
    if not HEARTBEAT.exists():
        return None
    try:
        return json.loads(HEARTBEAT.read_text(encoding="utf-8"))
    except Exception:
        return None


def last_hypothesis_before_crash(rows: list[dict]) -> str | None:
    """Hypothesis from the sterile/progress row immediately before a crash streak."""
    for i in range(len(rows) - 1, -1, -1):
        if not _is_crash_row(rows[i]):
            continue
        for j in range(i - 1, -1, -1):
            hyp = rows[j].get("hypothesis")
            if hyp and rows[j].get("label") in ("sterile", "progress", "flat"):
                return str(hyp)[:200]
            if _is_crash_row(rows[j]):
                continue
            break
    return None


def opportunistic_crash_brief(st: dict, budget: dict) -> str:
    """Return a short post-mortem block only when the ledger suggests improvising.

    Silent (empty) when recent history is healthy — do not nag every cycle.
    """
    rows = [r for r in tail_ledger(30) if r.get("strategy_id") == "agentic"]
    if not rows:
        return ""

    recent = rows[-8:]
    crashes = [r for r in recent if _is_crash_row(r)]
    if not crashes and not st.get("crashed_hint"):
        return ""

    tips: list[str] = []
    n_to = sum(1 for r in recent if _is_timeout_row(r))
    n_active = sum(
        1
        for r in recent
        if "active run" in str(r.get("missing") or "").lower()
        or "active run" in str(r.get("error") or "").lower()
    )
    n_detach = sum(
        1
        for r in recent
        if "detach" in str(r.get("missing") or "").lower()
        or "detach" in str(r.get("error") or "").lower()
    )
    n_mid = sum(
        1
        for r in recent
        if "mid-cycle" in str(r.get("missing") or "").lower()
        or "run dead" in str(r.get("missing") or "").lower()
    )

    # Only speak when something actionable happened recently
    last = recent[-1] if recent else {}
    last_was_bad = _is_crash_row(last) or bool(st.get("crashed_hint"))
    consec = int(st.get("consecutive_timeouts") or 0)
    # Opportunistic: skip entirely on a healthy streak (no open crash hint)
    if not last_was_bad and consec == 0 and not st.get("crashed_hint"):
        return ""
    if not last_was_bad and n_to < 1 and n_active < 1 and n_detach < 1 and n_mid < 1:
        return ""

    if n_to >= 1 or budget.get("mode") in ("wrap", "extend"):
        tips.append(
            "Timeout post-mortem: last wall-clock cancel(s) usually mean the experiment was "
            "unbounded (long search / no early result file). This cycle: smoke-first, write "
            "agent_cycle_result.json before any multi-hour tool, keep agent_heartbeat.json fresh."
        )
        hyp = last_hypothesis_before_crash(rows)
        if hyp:
            tips.append(
                f"Do NOT relaunch the same open-ended search that timed out. "
                f"Nearby prior hyp (context only): {hyp}"
            )
        hb = read_heartbeat()
        if hb and hb.get("status"):
            tips.append(
                f"Last heartbeat before cancel/restart: status={hb.get('status')} "
                f"eta_s={hb.get('eta_s')} — resume that thread only if you can finish under budget."
            )

    if n_active >= 1 or n_detach >= 1 or n_mid >= 1:
        tips.append(
            "Lifecycle post-mortem: active-run / detached / mid-cycle dead runs are director "
            "infra issues — force a clean agent if needed, do not invent a duplicate hypothesis "
            "for the crashed cycle; start a new bounded one."
        )

    if not tips:
        return ""

    # Opportunistic learnings append — only once per crash reason fingerprint
    fingerprint = f"to={n_to}|active={n_active}|detach={n_detach}|mid={n_mid}|mode={budget.get('mode')}"
    if st.get("last_crash_brief_fp") != fingerprint and last_was_bad:
        st["last_crash_brief_fp"] = fingerprint
        append_learning(
            f"crash-brief {fingerprint}: "
            + ("; ".join(t.split(":")[0] for t in tips[:3]))
        )
        save_state(st)

    return (
        "\nOPPORTUNISTIC CRASH POST-MORTEM (use only if it helps this cycle; ignore if irrelevant):\n"
        + "\n".join(f"- {t}" for t in tips)
        + "\n"
    )


def choose_cycle_budget(
    base_timeout: float,
    timeout_max: float,
    st: dict,
) -> dict:
    """Pick wall-clock budget + brief mode from recent ledger outcomes.

    Modes:
      tight   — recent cycles finish fast; demand smoke-scale experiments
      normal  — default
      wrap    — last cycle timed out once; demand early result write + modest wall
      extend  — repeated timeouts while agent was working; longer wall + still demand bounds
    """
    rows = [r for r in tail_ledger(24) if r.get("strategy_id") == "agentic"]
    recent = rows[-6:]
    n_to = sum(
        1
        for r in recent
        if r.get("timed_out") or r.get("missing") == "timed_out"
    )
    sterile_elapsed = [
        float(r["elapsed_s"])
        for r in recent
        if r.get("label") == "sterile" and isinstance(r.get("elapsed_s"), (int, float))
    ]
    consecutive = int(st.get("consecutive_timeouts") or 0)
    if n_to:
        # refresh from trailing timeouts at end of ledger
        consec = 0
        for r in reversed(rows):
            if r.get("timed_out") or r.get("missing") == "timed_out":
                consec += 1
            elif r.get("label") in ("sterile", "progress", "flat"):
                break
        consecutive = max(consecutive, consec)

    mode = "normal"
    timeout = float(base_timeout)
    if consecutive >= 2:
        mode = "extend"
        timeout = min(float(timeout_max), base_timeout * 1.5)
    elif consecutive == 1 or n_to >= 1:
        mode = "wrap"
        timeout = min(float(timeout_max), max(base_timeout, 3000.0))
    elif len(sterile_elapsed) >= 3 and sum(sterile_elapsed) / len(sterile_elapsed) < 600:
        mode = "tight"
        timeout = min(base_timeout, 2400.0)

    soft_at = timeout * 0.72
    grace_s = min(900.0, timeout * 0.28)
    notes = {
        "tight": (
            "BUDGET MODE=tight: recent cycles finish in minutes. "
            "Run a SMOKE-SCALE experiment only (≤2–5 min compute: e.g. ≤2k rounds / tiny beam). "
            "Write agent_cycle_result.json as soon as the smoke finishes — do not launch multi-hour searches."
        ),
        "normal": (
            "BUDGET MODE=normal: one bounded experiment. Prefer a quick smoke first, then at most one "
            "scaled run that fits comfortably under the wall clock. Update logs/agent_heartbeat.json "
            "every few minutes while a long tool runs."
        ),
        "wrap": (
            "BUDGET MODE=wrap: the previous cycle TIMED OUT. This cycle MUST finish with a result file. "
            "Do NOT start open-ended searches. Smoke-only (≤10 min), write agent_cycle_result.json early, stop. "
            "Keep logs/agent_heartbeat.json fresh if anything runs >2 min."
        ),
        "extend": (
            "BUDGET MODE=extend: repeated timeouts — wall clock is longer THIS cycle, but you still must "
            "bound work. Split: (1) write a tiny tool, (2) smoke ≤5 min, (3) write result. "
            "If a longer run is essential, update logs/agent_heartbeat.json every 2–3 min with status+eta_s "
            "so the outer director can grant grace instead of cancelling."
        ),
    }
    return {
        "mode": mode,
        "timeout_s": timeout,
        "soft_at": soft_at,
        "grace_s": grace_s,
        "timeout_max": float(timeout_max),
        "consecutive_timeouts": consecutive,
        "note": notes[mode],
    }


def agent_showing_progress(cycle_started_ts: float | None, stale_s: float = 180.0) -> tuple[bool, str]:
    """True if heartbeat / result / tools look freshly touched since cycle start."""
    now = time.time()
    started = float(cycle_started_ts or 0)

    if HEARTBEAT.exists():
        try:
            hb = json.loads(HEARTBEAT.read_text(encoding="utf-8"))
            hb_ts = float(hb.get("ts") or HEARTBEAT.stat().st_mtime)
            if hb_ts >= started - 1 and (now - hb_ts) <= stale_s:
                return True, f"heartbeat age={now - hb_ts:.0f}s status={hb.get('status')}"
        except Exception:
            if HEARTBEAT.stat().st_mtime >= started - 1 and (now - HEARTBEAT.stat().st_mtime) <= stale_s:
                return True, "heartbeat file fresh"

    if CYCLE_RESULT.exists() and CYCLE_RESULT.stat().st_mtime >= started - 1:
        return True, "agent_cycle_result present"

    newest = 0.0
    for p in (ROOT / "tools").glob("*.py"):
        newest = max(newest, p.stat().st_mtime)
    for p in (ROOT / "submissions").glob("director-agentic-*/**/*"):
        try:
            newest = max(newest, p.stat().st_mtime)
        except OSError:
            pass
    if newest >= started - 1 and (now - newest) <= stale_s:
        return True, f"workspace mtime age={now - newest:.0f}s"

    return False, "no fresh heartbeat/result/tool activity"


def build_brief(st: dict, budget: dict) -> str:
    ensure_learnings()
    best = st.get("best") or {}
    learnings = LEARNINGS.read_text(encoding="utf-8")[:4000]
    last = tail_ledger(10)
    crash = st.get("crashed_hint")
    crash_block = (
        f"\nPREVIOUS CYCLE CRASHED mid-flight: {crash}\n"
        "Inspect dirty tools/ and submissions/ before rewriting. "
        "Do not invent a duplicate of that failed cycle.\n"
        if crash
        else ""
    )
    postmortem = opportunistic_crash_brief(st, budget)
    timeout_s = float(budget["timeout_s"])
    return f"""You are the local Agentic Research Director for the Autolab hill
matrix-multiplication-tensor-3x3 in this repo (cwd is the project root).

{STERILE_FACTS}
{crash_block}{postmortem}
Current bests: additions={best.get('additions')} support={best.get('support')} rank={best.get('rank')}
Wall-clock budget this cycle: ~{int(timeout_s)}s (soft checkpoint ~{int(budget['soft_at'])}s).
{budget['note']}

Learnings file (also on disk at tools/learnings.md):
{learnings}

Last ledger rows:
{json.dumps(last, indent=2)[:3500]}

Recent tools/:
{chr(10).join(recent_tool_files())}

MANDATE for this cycle:
1. Propose ONE non-duplicate hypothesis that could beat adds<56 or support<152 or rank<23.
2. You MAY write a new tool under tools/ and run a BOUNDDED search (smoke first).
3. While any tool runs >2 minutes, refresh logs/agent_heartbeat.json roughly every 2–3 minutes:
   {{"ts": <unix_seconds>, "status": "short status", "eta_s": <seconds or null>, "cycle": {st.get('cycle', 0)}}}
   Fresh heartbeats let the outer director GRANT GRACE instead of cancelling at the soft deadline.
4. Do NOT hills push / Autolab publish. Do NOT force-push. Do NOT touch secrets/.env.
5. If you find Brent-ok improvement, write submission under submissions/director-agentic-*/ and note it.
6. When done, MUST write logs/agent_cycle_result.json with exactly this schema:
{{
  "hypothesis": "...",
  "actions": ["..."],
  "arch": "additions|support|rank",
  "metric_best": <number>,
  "improved": true/false,
  "out_dir": "submissions/..." or null,
  "next_hint": "...",
  "sterile": true/false
}}
Then stop. Prefer inventing new structure over re-running retired registry seeds.
Prefer finishing with a result over a heroic search that times out.
"""


def update_journal(st: dict, last: dict) -> None:
    if not JOURNAL.exists():
        return
    html = JOURNAL.read_text(encoding="utf-8")
    loop = (
        f"agentic director cycle={st.get('cycle', 0)} · "
        f"best adds={st['best'].get('additions')} support={st['best'].get('support')} "
        f"rank={st['best'].get('rank')} · last={last.get('label')} "
        f"({last.get('hypothesis', '')[:60]})"
    )
    new, n = re.subn(
        r"(<div><strong>Loop</strong>)[^<]*(</div>)",
        rf"\1 {loop}\2",
        html,
        count=1,
    )
    if n:
        JOURNAL.write_text(new, encoding="utf-8")
    phase = (
        f'<div><strong>Phase</strong> agentic Cursor SDK director '
        f'(local · caffeinate overnight)</div>'
    )
    new2, n2 = re.subn(
        r"<div><strong>Phase</strong>[^<]*</div>",
        phase,
        new if n else html,
        count=1,
    )
    if n2:
        JOURNAL.write_text(new2, encoding="utf-8")


def read_cycle_result() -> dict | None:
    if not CYCLE_RESULT.exists():
        return None
    try:
        return json.loads(CYCLE_RESULT.read_text(encoding="utf-8"))
    except Exception:
        return None


def ingest_result(st: dict, result: dict, run_meta: dict) -> dict:
    arch = result.get("arch") or "additions"
    metric = result.get("metric_best")
    improved = bool(result.get("improved"))
    if isinstance(metric, (int, float)) and improved:
        key = {"additions": "additions", "support": "support", "rank": "rank"}.get(arch, arch)
        cur = st["best"].get(key)
        if cur is None or metric < cur:
            st["best"][key] = int(metric)

    event = {
        "cycle": st.get("cycle"),
        "strategy_id": "agentic",
        "arch": arch,
        "label": "progress" if improved else ("sterile" if result.get("sterile") else "flat"),
        "best": metric,
        "hypothesis": result.get("hypothesis"),
        "actions": result.get("actions"),
        "out_dir": result.get("out_dir"),
        "next_hint": result.get("next_hint"),
        "improved": improved,
        "sterile": bool(result.get("sterile")),
        "agent_id": st.get("agent_id"),
        "run_id": st.get("run_id"),
        **{k: run_meta.get(k) for k in ("exit_status", "elapsed_s", "timed_out", "error")},
    }
    append_ledger(event)
    append_learning(
        f"cycle={st.get('cycle')} label={event['label']} arch={arch} "
        f"metric={metric} hyp={(result.get('hypothesis') or '')[:120]}"
    )
    if CYCLE_RESULT.exists():
        st["last_result_ingested_mtime"] = CYCLE_RESULT.stat().st_mtime
    update_journal(st, event)
    return event


def maybe_hills_eval(result: dict) -> None:
    if not result.get("improved"):
        return
    out = result.get("out_dir")
    if not out:
        return
    path = ROOT / out
    if not (path / "solution.json").exists() and path.suffix != ".json":
        return
    target = path if path.is_dir() else path.parent
    try:
        proc = subprocess.run(
            ["hills", "eval", str(target)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        log(f"hills eval exit={proc.returncode} tail={(proc.stdout or proc.stderr or '')[-500:]}")
    except FileNotFoundError:
        log("hills CLI not found — skip eval")
    except Exception as e:
        log(f"hills eval error: {e}")


def _import_sdk():
    try:
        from cursor_sdk import Agent, LocalAgentOptions, CursorAgentError  # type: ignore
    except ImportError as e:
        raise SystemExit(
            "cursor_sdk not importable. Use .venv (Python>=3.10): "
            "uv venv .venv --python 3.12 && uv pip install -r requirements.txt\n"
            f"Import error: {e}"
        ) from e
    return Agent, LocalAgentOptions, CursorAgentError


def open_agent(st: dict, api_key: str, model: str):
    Agent, LocalAgentOptions, _ = _import_sdk()
    from cursor_sdk import AgentOptions  # type: ignore

    local = LocalAgentOptions(cwd=str(ROOT))
    opts = AgentOptions(api_key=api_key, model=model, local=local)
    force_new = bool(st.get("force_new_agent"))
    if st.get("agent_id") and not force_new:
        try:
            log(f"resuming agent_id={st['agent_id']}")
            agent = Agent.resume(st["agent_id"], opts)
            return agent
        except Exception as e:
            log(f"resume failed ({e}); creating new agent")
    agent = Agent.create(
        api_key=api_key,
        model=model,
        local=local,
        name="laderman-agentic-director",
    )
    aid = getattr(agent, "agent_id", None) or getattr(agent, "agentId", None)
    st["agent_id"] = aid
    st["force_new_agent"] = False
    save_state(st)
    log(f"created agent_id={aid}")
    return agent


def cancel_stuck_run(st: dict, api_key: str) -> None:
    run_id = st.get("run_id")
    agent_id = st.get("agent_id")
    if not run_id and not agent_id:
        return
    Agent, _, _ = _import_sdk()
    try:
        if run_id:
            log(f"cancel_run run_id={run_id}")
            Agent.cancel_run(run_id, agent_id=agent_id)
    except Exception as e:
        log(f"cancel_run failed: {e}")
    try:
        if agent_id:
            Agent.archive(agent_id, {"api_key": api_key})
            log(f"archived agent_id={agent_id}")
    except Exception as e:
        log(f"archive failed: {e}")
    st["run_id"] = None
    st["agent_id"] = None
    st["force_new_agent"] = True
    save_state(st)


def wait_run_with_timeout(run, timeout_s: float, CursorAgentError, budget: dict | None = None, st: dict | None = None):
    """Wait for run with soft deadline + progress-based grace before hard cancel."""
    import threading

    budget = budget or {
        "timeout_s": timeout_s,
        "soft_at": timeout_s * 0.72,
        "grace_s": min(900.0, timeout_s * 0.28),
        "timeout_max": timeout_s,
        "mode": "normal",
    }
    hard = float(budget["timeout_s"])
    soft = float(budget["soft_at"])
    grace_s = float(budget["grace_s"])
    hard_cap = float(budget.get("timeout_max") or hard)
    started = (st or {}).get("cycle_started_ts") or time.time()

    t0 = time.time()
    box: dict = {"result": None, "error": None}

    def _wait():
        try:
            box["result"] = run.wait()
        except Exception as e:
            box["error"] = e

    th = threading.Thread(target=_wait, daemon=True)
    th.start()

    soft_logged = False
    grace_used = False
    poll = 15.0
    while th.is_alive():
        if STOP:
            break
        elapsed = time.time() - t0
        # Soft checkpoint: only log; cannot follow-up while run is active
        if elapsed >= soft and not soft_logged:
            soft_logged = True
            alive, why = agent_showing_progress(started)
            log(f"SOFT deadline {elapsed:.0f}s/{hard:.0f}s mode={budget.get('mode')} progress={alive} ({why})")
        # Hard deadline with optional one-shot grace if agent still working
        if elapsed >= hard:
            alive, why = agent_showing_progress(started, stale_s=240.0)
            if alive and not grace_used and hard + grace_s <= hard_cap + 1:
                grace_used = True
                hard = min(hard_cap, hard + grace_s)
                log(f"GRACE +{grace_s:.0f}s → hard={hard:.0f}s because {why}")
            elif alive and not grace_used and hard < hard_cap:
                grace_used = True
                hard = hard_cap
                log(f"GRACE to timeout_max={hard:.0f}s because {why}")
            else:
                log(
                    f"TIMEOUT after {elapsed:.0f}s (mode={budget.get('mode')} "
                    f"progress={alive} {why}) — cancelling run"
                )
                try:
                    if hasattr(run, "supports") and run.supports("cancel"):
                        run.cancel()
                    elif hasattr(run, "cancel"):
                        run.cancel()
                except Exception as e:
                    log(f"cancel failed: {e}")
                th.join(timeout=30)
                return None, elapsed, True, "timed_out"
        th.join(timeout=poll)

    elapsed = time.time() - t0
    if th.is_alive():
        log(f"TIMEOUT after {elapsed:.0f}s (interrupt) — cancelling run")
        try:
            if hasattr(run, "supports") and run.supports("cancel"):
                run.cancel()
            elif hasattr(run, "cancel"):
                run.cancel()
        except Exception as e:
            log(f"cancel failed: {e}")
        th.join(timeout=30)
        return None, elapsed, True, "timed_out"
    if box["error"] is not None:
        return None, elapsed, False, str(box["error"])
    return box["result"], elapsed, False, None


def recover_on_startup(
    st: dict,
    api_key: str,
    model: str,
    base_timeout: float,
    timeout_max: float,
) -> dict:
    """Handle mid-cycle crash / unfinished result before starting new cycles."""
    phase = st.get("phase") or "idle"
    result = read_cycle_result()
    mtime = CYCLE_RESULT.stat().st_mtime if CYCLE_RESULT.exists() else None
    started = st.get("cycle_started_ts")
    ingested = st.get("last_result_ingested_mtime")

    # Finalize orphan result
    if (
        result
        and mtime is not None
        and (ingested is None or mtime > float(ingested or 0))
        and started
        and mtime >= float(started) - 1
    ):
        log("recovery: ingesting orphan agent_cycle_result.json")
        st["phase"] = "finalizing"
        save_state(st)
        event = ingest_result(st, result, {"exit_status": "recovered", "elapsed_s": None, "timed_out": False})
        maybe_hills_eval(result)
        st["phase"] = "idle"
        st["run_id"] = None
        st["crashed_hint"] = None
        st["consecutive_timeouts"] = 0
        save_state(st)
        return st

    if phase in ("prompting", "awaiting_result") and st.get("agent_id"):
        log(f"recovery: phase={phase} agent_id={st.get('agent_id')} run_id={st.get('run_id')}")
        Agent, LocalAgentOptions, CursorAgentError = _import_sdk()
        from cursor_sdk import AgentOptions  # type: ignore

        budget = choose_cycle_budget(base_timeout, timeout_max, st)
        st["budget_mode"] = budget["mode"]
        try:
            agent = Agent.resume(
                st["agent_id"],
                AgentOptions(
                    api_key=api_key,
                    model=model,
                    local=LocalAgentOptions(cwd=str(ROOT)),
                ),
            )
            run_id = st.get("run_id")
            if run_id:
                try:
                    run = Agent.get_run(run_id, {"api_key": api_key})
                    log(
                        f"recovery: reattached run_id={run_id}; "
                        f"budget_mode={budget['mode']} timeout={budget['timeout_s']:.0f}s"
                    )
                    st["phase"] = "awaiting_result"
                    save_state(st)
                    res, elapsed, timed_out, err = wait_run_with_timeout(
                        run,
                        budget["timeout_s"],
                        CursorAgentError,
                        budget=budget,
                        st=st,
                    )
                    # Detached / already-done runs often error immediately
                    if err and "detach" in err.lower():
                        log(f"recovery: detached run — cancelling: {err}")
                        try:
                            agent.close()
                        except Exception:
                            pass
                        cancel_stuck_run(st, api_key)
                        append_ledger(
                            {
                                "cycle": st.get("cycle"),
                                "strategy_id": "agentic",
                                "label": "crashed",
                                "arch": "unknown",
                                "missing": f"detached run: {err}",
                                "agent_id": st.get("agent_id"),
                                "run_id": run_id,
                            }
                        )
                        st["crashed_hint"] = f"detached run_id={run_id}"
                        st["phase"] = "idle"
                        st["cycle"] = int(st.get("cycle") or 0) + 1
                        save_state(st)
                        return st
                    return _finish_after_wait(st, agent, res, elapsed, timed_out, err)
                except Exception as e:
                    log(f"recovery: get_run/wait failed: {e}")
            # No live run — mark crashed and force new agent
            try:
                agent.close()
            except Exception:
                pass
            cancel_stuck_run(st, api_key)
        except Exception as e:
            log(f"recovery: resume failed: {e}")

        append_ledger(
            {
                "cycle": st.get("cycle"),
                "strategy_id": "agentic",
                "label": "crashed",
                "arch": "unknown",
                "best": None,
                "missing": "mid-cycle crash; run dead on resume",
                "agent_id": st.get("agent_id"),
                "run_id": st.get("run_id"),
            }
        )
        st["crashed_hint"] = (
            f"cycle={st.get('cycle')} run_id={st.get('run_id')} phase={phase}"
        )
        st["phase"] = "idle"
        st["run_id"] = None
        # bump cycle so we do not reuse the same cycle number for a new hypothesis
        st["cycle"] = int(st.get("cycle") or 0) + 1
        save_state(st)
        update_journal(st, {"label": "crashed", "hypothesis": st["crashed_hint"]})
    elif phase != "idle":
        st["phase"] = "idle"
        save_state(st)
    return st


def _finish_after_wait(st, agent, res, elapsed, timed_out, err) -> dict:
    st["phase"] = "finalizing"
    save_state(st)
    status = getattr(res, "status", None) if res is not None else None
    if timed_out:
        hb = read_heartbeat()
        partial = read_cycle_result()
        tip_bits = []
        if hb and hb.get("status"):
            tip_bits.append(f"heartbeat={hb.get('status')} eta_s={hb.get('eta_s')}")
        if partial and partial.get("hypothesis"):
            tip_bits.append(f"partial_hyp={(partial.get('hypothesis') or '')[:120]}")
        tools_touch = recent_tool_files(3)
        if tools_touch:
            tip_bits.append(f"recent_tools={','.join(tools_touch)}")
        detail = "; ".join(tip_bits) if tip_bits else "no heartbeat/partial result"
        append_ledger(
            {
                "cycle": st.get("cycle"),
                "strategy_id": "agentic",
                "label": "crashed",
                "arch": "unknown",
                "timed_out": True,
                "elapsed_s": elapsed,
                "agent_id": st.get("agent_id"),
                "run_id": st.get("run_id"),
                "missing": "timed_out",
                "budget_mode": st.get("budget_mode"),
                "postmortem": detail,
                "hypothesis": (partial or {}).get("hypothesis") if partial else None,
            }
        )
        st["crashed_hint"] = (
            f"timeout cycle={st.get('cycle')} run_id={st.get('run_id')} | {detail}"
        )
        st["consecutive_timeouts"] = int(st.get("consecutive_timeouts") or 0) + 1
        # Opportunistic learning only on timeout (next brief may reuse via post-mortem)
        append_learning(
            f"TIMEOUT cycle={st.get('cycle')} mode={st.get('budget_mode')} {detail} "
            "→ next: smoke-bound + early agent_cycle_result.json"
        )
        st["phase"] = "idle"
        st["run_id"] = None
        save_state(st)
        return st

    if err or status == "error":
        append_ledger(
            {
                "cycle": st.get("cycle"),
                "strategy_id": "agentic",
                "label": "crashed",
                "arch": "unknown",
                "elapsed_s": elapsed,
                "exit_status": status or "error",
                "error": err,
                "agent_id": st.get("agent_id"),
                "run_id": st.get("run_id"),
            }
        )
        st["crashed_hint"] = f"error cycle={st.get('cycle')} status={status} err={err}"
        st["phase"] = "idle"
        st["run_id"] = None
        save_state(st)
        return st

    result = read_cycle_result()
    if result:
        event = ingest_result(
            st,
            result,
            {"exit_status": status or "finished", "elapsed_s": elapsed, "timed_out": False},
        )
        maybe_hills_eval(result)
        log(
            f"SCOREBOARD adds={st['best'].get('additions')} support={st['best'].get('support')} "
            f"rank={st['best'].get('rank')} | last={event.get('label')} | hyp={event.get('hypothesis')}"
        )
        st["crashed_hint"] = None
        st["consecutive_timeouts"] = 0
    else:
        append_ledger(
            {
                "cycle": st.get("cycle"),
                "strategy_id": "agentic",
                "label": "flat",
                "arch": "unknown",
                "elapsed_s": elapsed,
                "exit_status": status,
                "missing": "run finished without agent_cycle_result.json",
                "agent_id": st.get("agent_id"),
                "run_id": st.get("run_id"),
            }
        )
        log("cycle finished but logs/agent_cycle_result.json missing")

    st["phase"] = "idle"
    st["run_id"] = None
    save_state(st)
    return st


def run_one_cycle(
    st: dict,
    api_key: str,
    model: str,
    base_timeout: float,
    timeout_max: float,
) -> bool:
    Agent, LocalAgentOptions, CursorAgentError = _import_sdk()
    budget = choose_cycle_budget(base_timeout, timeout_max, st)
    st["cycle"] = int(st.get("cycle") or 0) + 1
    st["cycle_started_ts"] = time.time()
    st["phase"] = "prompting"
    st["budget_mode"] = budget["mode"]
    if CYCLE_RESULT.exists():
        CYCLE_RESULT.unlink()
    if HEARTBEAT.exists():
        try:
            HEARTBEAT.unlink()
        except OSError:
            pass
    save_state(st)

    brief = build_brief(st, budget)
    agent = open_agent(st, api_key, model)
    try:
        log(
            f"RUN cycle={st['cycle']} agent_id={st.get('agent_id')} "
            f"budget_mode={budget['mode']} timeout={budget['timeout_s']:.0f}s "
            f"soft={budget['soft_at']:.0f}s grace={budget['grace_s']:.0f}s "
            f"consec_to={budget['consecutive_timeouts']}"
        )
        run = agent.send(brief)
        run_id = getattr(run, "id", None) or getattr(run, "run_id", None)
        st["run_id"] = run_id
        st["phase"] = "awaiting_result"
        save_state(st)
        log(f"run_id={run_id}")

        res, elapsed, timed_out, err = wait_run_with_timeout(
            run,
            budget["timeout_s"],
            CursorAgentError,
            budget=budget,
            st=st,
        )
        _finish_after_wait(st, agent, res, elapsed, timed_out, err)
    except CursorAgentError as e:
        msg = str(getattr(e, "message", e))
        log(f"CursorAgentError: {msg} retryable={getattr(e, 'is_retryable', None)}")
        append_ledger(
            {
                "cycle": st.get("cycle"),
                "strategy_id": "agentic",
                "label": "crashed",
                "missing": f"CursorAgentError: {msg}",
                "agent_id": st.get("agent_id"),
            }
        )
        st["crashed_hint"] = msg
        if "already has active run" in msg.lower() or "active run" in msg.lower():
            cancel_stuck_run(st, api_key)
        st["phase"] = "idle"
        st["run_id"] = None
        st["force_new_agent"] = True
        save_state(st)
        return False
    finally:
        try:
            agent.close()
        except Exception:
            pass
    return True


def smoke_pong(api_key: str, model: str) -> None:
    Agent, LocalAgentOptions, CursorAgentError = _import_sdk()
    from cursor_sdk import AgentOptions  # type: ignore

    log("smoke: Agent.prompt pong")
    try:
        result = Agent.prompt(
            "Reply with exactly the word pong and nothing else.",
            AgentOptions(
                api_key=api_key,
                model=model,
                local=LocalAgentOptions(cwd=str(ROOT)),
            ),
        )
        log(f"smoke status={getattr(result, 'status', None)} result={getattr(result, 'result', result)!r}"[:500])
        if getattr(result, "status", None) == "error":
            raise SystemExit(2)
    except CursorAgentError as e:
        log(f"smoke failed: {getattr(e, 'message', e)}")
        raise SystemExit(1) from e


def main() -> int:
    ap = argparse.ArgumentParser(description="Local Cursor Agent SDK research director")
    ap.add_argument("--max-cycles", type=int, default=20)
    ap.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="Base per-cycle wall seconds (adaptive modes may shorten/extend)",
    )
    ap.add_argument(
        "--timeout-max",
        type=float,
        default=DEFAULT_TIMEOUT_MAX,
        help="Hard cap for extend/grace (seconds)",
    )
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="Agent.prompt pong then exit")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--no-recover", action="store_true")
    args = ap.parse_args()

    signal.signal(signal.SIGINT, _on_sig)
    signal.signal(signal.SIGTERM, _on_sig)
    os.chdir(ROOT)
    (ROOT / "logs").mkdir(parents=True, exist_ok=True)
    ensure_learnings()

    api_key = require_api_key()
    if args.smoke:
        smoke_pong(api_key, args.model)
        return 0

    st = load_state()
    # Preserve historical cycle count from registry director if present
    if "best" not in st:
        st["best"] = {"additions": 56, "support": 152, "rank": 23}

    log(
        f"agentic director start max_cycles={args.max_cycles} "
        f"timeout={args.timeout}s timeout_max={args.timeout_max}s "
        f"model={args.model} phase={st.get('phase')} agent_id={st.get('agent_id')}"
    )

    if not args.no_recover:
        st = recover_on_startup(st, api_key, args.model, args.timeout, args.timeout_max)

    cycles = 0
    while cycles < args.max_cycles and not STOP:
        ok = run_one_cycle(st, api_key, args.model, args.timeout, args.timeout_max)
        cycles += 1
        st = load_state()
        if args.once or not ok:
            break

    st = load_state()
    log(f"agentic director stop cycles_run={cycles} state_cycle={st.get('cycle')} best={st.get('best')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
