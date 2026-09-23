#!/usr/bin/env python3
"""Local Cursor Agent SDK research director for the 3×3 tensor climb.

Outer Python loop + durable local agent that improvises from the experiment
ledger (not a fixed strategies.json queue).

  .venv/bin/python -u tools/agentic_director.py --once
  .venv/bin/python -u tools/agentic_director.py --max-cycles 20 --timeout 2400
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

STOP = False
DEFAULT_MODEL = "composer-2.5"

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


def build_brief(st: dict, timeout_s: float) -> str:
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
    return f"""You are the local Agentic Research Director for the Autolab hill
matrix-multiplication-tensor-3x3 in this repo (cwd is the project root).

{STERILE_FACTS}
{crash_block}
Current bests: additions={best.get('additions')} support={best.get('support')} rank={best.get('rank')}
Cycle budget: finish within ~{int(timeout_s)}s wall clock. Prefer one bounded experiment.

Learnings file (also on disk at tools/learnings.md):
{learnings}

Last ledger rows:
{json.dumps(last, indent=2)[:3500]}

Recent tools/:
{chr(10).join(recent_tool_files())}

MANDATE for this cycle:
1. Propose ONE non-duplicate hypothesis that could beat adds<56 or support<152 or rank<23.
2. You MAY write a new tool under tools/ and run a BOUNDDED search (small rounds first).
3. Do NOT hills push / Autolab publish. Do NOT force-push. Do NOT touch secrets/.env.
4. If you find Brent-ok improvement, write submission under submissions/director-agentic-*/ and note it.
5. When done, MUST write logs/agent_cycle_result.json with exactly this schema:
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


def wait_run_with_timeout(run, timeout_s: float, CursorAgentError):
    """Wait for run; cancel on timeout when supported."""
    t0 = time.time()
    # Prefer SDK wait with no built-in timeout — poll via wait in a thread? sync wait blocks.
    # Use a simple approach: call wait() and rely on outer signal; for timeout use cancel.
    import threading

    box: dict = {"result": None, "error": None}

    def _wait():
        try:
            box["result"] = run.wait()
        except Exception as e:
            box["error"] = e

    th = threading.Thread(target=_wait, daemon=True)
    th.start()
    th.join(timeout=timeout_s)
    elapsed = time.time() - t0
    if th.is_alive():
        log(f"TIMEOUT after {elapsed:.0f}s — cancelling run")
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
        err = box["error"]
        return None, elapsed, False, str(err)
    return box["result"], elapsed, False, None


def recover_on_startup(st: dict, api_key: str, model: str, timeout_s: float) -> dict:
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
        save_state(st)
        return st

    if phase in ("prompting", "awaiting_result") and st.get("agent_id"):
        log(f"recovery: phase={phase} agent_id={st.get('agent_id')} run_id={st.get('run_id')}")
        Agent, LocalAgentOptions, CursorAgentError = _import_sdk()
        from cursor_sdk import AgentOptions  # type: ignore

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
                    log(f"recovery: reattached run_id={run_id}; waiting remaining timeout")
                    st["phase"] = "awaiting_result"
                    save_state(st)
                    res, elapsed, timed_out, err = wait_run_with_timeout(run, timeout_s, CursorAgentError)
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
            }
        )
        st["crashed_hint"] = f"timeout cycle={st.get('cycle')} run_id={st.get('run_id')}"
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


def run_one_cycle(st: dict, api_key: str, model: str, timeout_s: float) -> bool:
    Agent, LocalAgentOptions, CursorAgentError = _import_sdk()
    st["cycle"] = int(st.get("cycle") or 0) + 1
    st["cycle_started_ts"] = time.time()
    st["phase"] = "prompting"
    if CYCLE_RESULT.exists():
        # avoid mistaking old result for this cycle
        CYCLE_RESULT.unlink()
    save_state(st)

    brief = build_brief(st, timeout_s)
    agent = open_agent(st, api_key, model)
    try:
        log(f"RUN cycle={st['cycle']} agent_id={st.get('agent_id')} timeout={timeout_s}s")
        run = agent.send(brief)
        run_id = getattr(run, "id", None) or getattr(run, "run_id", None)
        st["run_id"] = run_id
        st["phase"] = "awaiting_result"
        save_state(st)
        log(f"run_id={run_id}")

        # Do NOT iterate run.messages() before wait — it blocks until the run
        # finishes and defeats the wall-clock timeout. Wait with timeout only.
        res, elapsed, timed_out, err = wait_run_with_timeout(run, timeout_s, CursorAgentError)
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
    ap.add_argument("--timeout", type=float, default=2400.0, help="Per-cycle seconds")
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
        f"agentic director start max_cycles={args.max_cycles} timeout={args.timeout}s "
        f"model={args.model} phase={st.get('phase')} agent_id={st.get('agent_id')}"
    )

    if not args.no_recover:
        st = recover_on_startup(st, api_key, args.model, args.timeout)

    cycles = 0
    while cycles < args.max_cycles and not STOP:
        ok = run_one_cycle(st, api_key, args.model, args.timeout)
        cycles += 1
        st = load_state()
        if args.once or not ok:
            break

    st = load_state()
    log(f"agentic director stop cycles_run={cycles} state_cycle={st.get('cycle')} best={st.get('best')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
