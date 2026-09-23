#!/usr/bin/env python3
"""Network-free Python agentic director (no Cursor SDK).

Same research loop as the SDK director — ledger + learnings + opportunistic
arch choice — but picks and runs local tools/ scripts itself.

  .venv/bin/python -u tools/python_agentic_director.py --once
  .venv/bin/python -u tools/python_agentic_director.py --max-cycles 50 --timeout 900
  bash tools/resume_overnight.sh --python   # LaunchAgent overnight

Does NOT call Cursor Agent API. Invents by composing smoke-scale argv for
discovered tools and recording sterile/progress in logs/experiments.jsonl.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import signal
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "logs" / "experiments.jsonl"
STATE = ROOT / "logs" / "director_state.json"
JOURNAL = ROOT / "journal.html"
DIR_LOG = ROOT / "logs" / "director.log"
LEARNINGS = ROOT / "tools" / "learnings.md"
QUEUE = ROOT / "logs" / "python_tool_queue.json"

STOP = False
DIRECTOR_ID = "python_agentic"

# Name → arch heuristic
ARCH_RULES = (
    (("support_", "support-"), "support"),
    (("rank_", "flipgraph", "schoolbook"), "rank"),
    (("slp_", "scheme_cse", "shave_"), "additions"),
)

SKIP_TOOLS = {
    "agentic_director.py",
    "python_agentic_director.py",
    "research_director.py",
    "director_dashboard.py",
    "checkpoint_sidecar.py",
    "launch_agents.sh",
}


def _on_sig(_sig, _frame):
    global STOP
    STOP = True
    log("interrupt — stop after current cycle")


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
    print(line, flush=True)
    DIR_LOG.parent.mkdir(parents=True, exist_ok=True)
    with DIR_LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "cycle": 0,
        "phase": "idle",
        "best": {"additions": 56, "support": 152, "rank": 23},
        "python_cursor": 0,
        "director": DIRECTOR_ID,
    }


def save_state(st: dict) -> None:
    st["director"] = DIRECTOR_ID
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, STATE)


def append_ledger(event: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    event = {**event, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "director": DIRECTOR_ID}
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def append_learning(note: str) -> None:
    LEARNINGS.parent.mkdir(parents=True, exist_ok=True)
    if not LEARNINGS.exists():
        LEARNINGS.write_text("# Research learnings\n\n## Updates\n", encoding="utf-8")
    with LEARNINGS.open("a", encoding="utf-8") as f:
        f.write(f"\n- {time.strftime('%Y-%m-%d %H:%M')} {note}\n")


def tail_ledger(n: int = 40) -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines()[-n:]:
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def classify_arch(name: str) -> str | None:
    low = name.lower()
    for keys, arch in ARCH_RULES:
        if any(k in low for k in keys):
            return arch
    return None


def discover_tools() -> list[dict]:
    tools = []
    for p in sorted((ROOT / "tools").glob("*.py")):
        if p.name in SKIP_TOOLS or p.name.startswith("_"):
            continue
        arch = classify_arch(p.name)
        if not arch:
            continue
        tools.append({"tool": f"tools/{p.name}", "name": p.name, "arch": arch})
    return tools


def recent_tool_uses() -> Counter:
    c: Counter = Counter()
    for r in tail_ledger(200):
        t = r.get("tool") or r.get("strategy_id")
        if t:
            c[Path(str(t)).name] += 1
    return c


def recent_arch_sterile() -> Counter:
    c: Counter = Counter()
    for r in tail_ledger(60):
        if r.get("label") == "sterile" and r.get("arch") in ("additions", "support", "rank"):
            c[r["arch"]] += 1
    return c


def choose_arch(rng: random.Random) -> str:
    """Opportunistic: prefer arches that are under-explored recently."""
    sterile = recent_arch_sterile()
    # Inverse sterile weight + small floor so all stay possible
    weights = {}
    for arch in ("additions", "support", "rank"):
        weights[arch] = 1.0 / (1.0 + sterile.get(arch, 0))
    # Slight bump if last cycle was sterile on one arch — try another
    last = tail_ledger(5)
    if last and last[-1].get("label") == "sterile":
        last_arch = last[-1].get("arch")
        if last_arch in weights:
            weights[last_arch] *= 0.55
    arches = list(weights)
    ws = [weights[a] for a in arches]
    return rng.choices(arches, weights=ws, k=1)[0]


def choose_tool(arch: str, rng: random.Random) -> dict | None:
    catalog = [t for t in discover_tools() if t["arch"] == arch]
    if not catalog:
        return None
    used = recent_tool_uses()
    # Prefer least-used; shuffle ties
    catalog.sort(key=lambda t: (used.get(t["name"], 0), rng.random()))
    return catalog[0]


def smoke_argv(tool: dict, cycle: int, out_dir: Path) -> list[str]:
    """Conservative smoke-scale flags shared across many tools."""
    name = tool["name"]
    seed = 700000 + cycle * 17
    help_txt = _tool_help(tool["tool"])

    def has(flag: str) -> bool:
        return flag in help_txt

    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-u", str(ROOT / tool["tool"])]
    if has("--src"):
        if tool["arch"] == "support":
            src = "submissions/stapleton60/solution.json"
        else:
            src = (
                "submissions/sun56/solution.json"
                if (ROOT / "submissions/sun56/solution.json").exists()
                else "submissions/stapleton60/solution.json"
            )
        if (ROOT / src).exists():
            cmd.extend(["--src", src])
    if has("--out"):
        cmd.extend(["--out", str(out_dir.relative_to(ROOT))])
    if has("--log"):
        cmd.extend(["--log", f"logs/python-{Path(name).stem}-{cycle}.log"])
    if has("--seed"):
        cmd.extend(["--seed", str(seed)])
    if has("--seed-base"):
        cmd.extend(["--seed-base", str(seed)])
    if has("--samples"):
        cmd.extend(["--samples", "400"])
    if has("--trials"):
        cmd.extend(["--trials", "800"])
    if has("--rounds"):
        cmd.extend(["--rounds", "800"])
    if has("--max-rounds"):
        cmd.extend(["--max-rounds", "800"])
    if has("--beam"):
        cmd.extend(["--beam", "8"])
    if has("--rebuild-seeds"):
        cmd.extend(["--rebuild-seeds", "6"])
    if has("--max-k"):
        cmd.extend(["--max-k", "2"])
    return cmd


_HELP_CACHE: dict[str, str] = {}


def _tool_help(rel: str) -> str:
    if rel in _HELP_CACHE:
        return _HELP_CACHE[rel]
    try:
        proc = subprocess.run(
            [sys.executable, str(ROOT / rel), "--help"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=20,
        )
        txt = (proc.stdout or "") + (proc.stderr or "")
    except Exception as e:
        txt = str(e)
    _HELP_CACHE[rel] = txt
    return txt


def parse_metric(arch: str, tail: str) -> tuple[float | None, bool]:
    """Return (metric_best, improved_hint)."""
    improved = False
    best = None
    if arch == "additions":
        for pat in (
            r"best_total=(\d+)",
            r"certified_cost=(\d+)",
            r"best_cost=(\d+)",
            r"best=(\d+)",
            r"total=(\d+)",
            r"cost ->\s*(\d+)",
        ):
            m = re.search(pat, tail)
            if m:
                best = int(m.group(1))
                break
        if best is not None and best < 56:
            improved = True
    elif arch == "support":
        for pat in (
            r"best_support=(\d+)",
            r"support\s*->\s*(\d+)",
            r"support=(\d+)",
            r"nnz=(\d+)",
        ):
            m = re.search(pat, tail)
            if m:
                best = int(m.group(1))
                break
        if best is not None and best < 152:
            improved = True
        if re.search(r"improved=([1-9]\d*)", tail):
            improved = True
    elif arch == "rank":
        m = re.search(r"HIT.*rank=(\d+)", tail)
        if m:
            best = int(m.group(1))
            improved = best < 23
        else:
            m = re.search(r"rank=(\d+)", tail)
            if m:
                best = int(m.group(1))
                improved = best < 23
    return best, improved


def run_cmd(cmd: list[str], timeout_s: float) -> dict:
    log(f"exec: {' '.join(cmd)}")
    t0 = time.time()
    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout_s)
        return {
            "exit_code": proc.returncode,
            "elapsed_s": time.time() - t0,
            "stdout_tail": "\n".join((stdout or "").splitlines()[-50:]),
            "stderr_tail": "\n".join((stderr or "").splitlines()[-20:]),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except Exception:
            proc.kill()
        try:
            stdout, stderr = proc.communicate(timeout=15)
        except Exception:
            stdout, stderr = "", ""
        return {
            "exit_code": -1,
            "elapsed_s": time.time() - t0,
            "stdout_tail": (stdout or "")[-2000:],
            "stderr_tail": (stderr or "")[-1000:],
            "timed_out": True,
        }


def update_journal(st: dict, last: dict) -> None:
    if not JOURNAL.exists():
        return
    html = JOURNAL.read_text(encoding="utf-8")
    loop = (
        f"python agentic director cycle={st.get('cycle', 0)} · "
        f"best adds={st['best'].get('additions')} support={st['best'].get('support')} "
        f"rank={st['best'].get('rank')} · last={last.get('label')} "
        f"({(last.get('hypothesis') or '')[:60]})"
    )
    new, n = re.subn(
        r"(<div><strong>Loop</strong>)[^<]*(</div>)",
        rf"\1 {loop}\2",
        html,
        count=1,
    )
    if n:
        html = new
    phase = (
        '<div><strong>Phase</strong> python agentic director '
        "(no Cursor SDK · LaunchAgent overnight)</div>"
    )
    new2, n2 = re.subn(r"<div><strong>Phase</strong>[^<]*</div>", phase, html, count=1)
    if n2:
        JOURNAL.write_text(new2, encoding="utf-8")
    elif n:
        JOURNAL.write_text(html, encoding="utf-8")


def run_one_cycle(st: dict, timeout_s: float, rng: random.Random) -> None:
    st["cycle"] = int(st.get("cycle") or 0) + 1
    st["phase"] = "running"
    st["cycle_started_ts"] = time.time()
    save_state(st)

    arch = choose_arch(rng)
    tool = choose_tool(arch, rng)
    if not tool:
        log(f"no tools for arch={arch}")
        append_ledger(
            {
                "cycle": st["cycle"],
                "strategy_id": DIRECTOR_ID,
                "label": "flat",
                "arch": arch,
                "missing": "no tools discovered",
            }
        )
        st["phase"] = "idle"
        save_state(st)
        return

    out_dir = ROOT / "submissions" / f"director-python-{Path(tool['name']).stem}-{st['cycle']}"
    hyp = (
        f"Python-agentic smoke on {tool['name']} for arch={arch} "
        f"(opportunistic; least-used tool bias)"
    )
    cmd = smoke_argv(tool, st["cycle"], out_dir)
    log(f"RUN cycle={st['cycle']} arch={arch} tool={tool['name']} timeout={timeout_s}s")
    meta = run_cmd(cmd, timeout_s)
    tail = (meta.get("stdout_tail") or "") + "\n" + (meta.get("stderr_tail") or "")
    metric, improved_hint = parse_metric(arch, tail)
    if meta.get("timed_out"):
        label = "crashed"
        improved = False
    elif improved_hint and metric is not None:
        key = arch
        cur = st["best"].get(key)
        if cur is None or metric < cur:
            st["best"][key] = int(metric)
            improved = True
            label = "progress"
        else:
            improved = False
            label = "sterile"
    else:
        improved = False
        label = "sterile" if meta.get("exit_code") == 0 else "flat"
        if metric is None:
            # defaults to current baseline for bookkeeping
            metric = {"additions": 56, "support": 152, "rank": 23}.get(arch)

    event = {
        "cycle": st["cycle"],
        "strategy_id": DIRECTOR_ID,
        "tool": tool["tool"],
        "arch": arch,
        "label": label,
        "best": metric,
        "hypothesis": hyp,
        "improved": improved,
        "sterile": label == "sterile",
        "elapsed_s": meta.get("elapsed_s"),
        "timed_out": meta.get("timed_out"),
        "exit_code": meta.get("exit_code"),
        "out_dir": str(out_dir.relative_to(ROOT)) if out_dir.exists() else None,
    }
    append_ledger(event)
    append_learning(
        f"python cycle={st['cycle']} label={label} arch={arch} "
        f"metric={metric} tool={tool['name']}"
    )
    update_journal(st, event)
    log(
        f"SCOREBOARD adds={st['best'].get('additions')} support={st['best'].get('support')} "
        f"rank={st['best'].get('rank')} | {label} | {tool['name']}"
    )
    st["phase"] = "idle"
    st["last_tool"] = tool["name"]
    st["last_arch"] = arch
    save_state(st)


def main() -> int:
    ap = argparse.ArgumentParser(description="Python agentic director (no Cursor SDK)")
    ap.add_argument("--max-cycles", type=int, default=50)
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    signal.signal(signal.SIGINT, _on_sig)
    signal.signal(signal.SIGTERM, _on_sig)
    os.chdir(ROOT)
    (ROOT / "logs").mkdir(parents=True, exist_ok=True)

    st = load_state()
    if "best" not in st:
        st["best"] = {"additions": 56, "support": 152, "rank": 23}
    rng = random.Random(args.seed if args.seed is not None else (st.get("cycle") or 0) + 42)

    n_tools = len(discover_tools())
    log(
        f"python agentic start max_cycles={args.max_cycles} timeout={args.timeout}s "
        f"tools={n_tools} best={st.get('best')}"
    )

    ran = 0
    while ran < args.max_cycles and not STOP:
        run_one_cycle(st, args.timeout, rng)
        ran += 1
        st = load_state()
        if args.once:
            break

    log(f"python agentic stop cycles_run={ran} state_cycle={st.get('cycle')} best={st.get('best')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
