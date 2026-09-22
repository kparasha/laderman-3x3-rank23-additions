#!/usr/bin/env python3
"""Pure-Python auto-research director for the 3×3 tensor climb.

Loops without human pivots:
  diagnose last run → retire sterile strategies → pick next (arch×tool)
  → bounded subprocess → append experiments.jsonl → update journal snippet
  → repeat until all strategies exhausted or --max-cycles / interrupt.

Arches (priority): additions → support → rank.
Network-free. Ledger: logs/experiments.jsonl · state: logs/director_state.json

  python3 -u tools/research_director.py --max-cycles 20
  python3 -u tools/research_director.py --once
  python3 -u tools/research_director.py --dry-run
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
STRATEGIES = ROOT / "tools" / "strategies.json"
LEDGER = ROOT / "logs" / "experiments.jsonl"
STATE = ROOT / "logs" / "director_state.json"
JOURNAL = ROOT / "journal.html"
DIR_LOG = ROOT / "logs" / "director.log"

STOP = False

FIXED_OUTS = {
    "slp_addition_search.py": ROOT / "submissions/attempt015-sun-cse",
    "slp_w_search.py": ROOT / "submissions/attempt015-additions",
    "flipgraph_search.py": ROOT / "submissions/attempt014-flipgraph",
    "shave_sun_slp.py": ROOT / "submissions/attempt010-sun-slp",
}

# Tools whose pass_positional[k] is an output *directory* (not solution.json)
DIR_OUT_TOOLS = {
    "scheme_cse_mutate.py": 1,
    "rank_drop_search.py": 1,
    "support_multiseed.py": 0,
}


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


def load_registry() -> dict:
    return json.loads(STRATEGIES.read_text(encoding="utf-8"))


def save_registry(reg: dict) -> None:
    tmp = STRATEGIES.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, STRATEGIES)


def append_ledger(event: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    event = {**event, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"cycle": 0, "best": {"additions": 56, "support": 152, "rank": 23}}


def save_state(st: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, STATE)


def read_json(path: Path | None) -> dict | None:
    if path is None or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def parse_paths(strat: dict):
    args = strat.get("args") or []
    ck_path = out = logp = None
    for i, a in enumerate(args):
        if a == "--out" and i + 1 < len(args):
            out = ROOT / args[i + 1]
        elif a == "--log" and i + 1 < len(args):
            logp = ROOT / args[i + 1]
        elif a == "--checkpoint" and i + 1 < len(args):
            ck_path = ROOT / args[i + 1]
    tool = Path(strat["tool"]).name
    if out is None and tool in FIXED_OUTS:
        out = FIXED_OUTS[tool]
    pos = strat.get("pass_positional") or []
    if out is None and tool in DIR_OUT_TOOLS and len(pos) > DIR_OUT_TOOLS[tool]:
        out = ROOT / pos[DIR_OUT_TOOLS[tool]]
    elif out is None and len(pos) >= 2:
        p = Path(pos[1])
        out = ROOT / (p.parent if p.suffix == ".json" else p)
    return ck_path, out, logp


def diagnose_from_artifacts(strat: dict) -> dict:
    ck_path, out, _logp = parse_paths(strat)
    ck = read_json(ck_path)
    cert = None
    sol = None
    if out:
        for name in ("slp_certificate.json", "support_certificate.json"):
            cert = read_json(out / name)
            if cert:
                break
        sol = read_json(out / "solution.json")

    diag: dict = {
        "strategy_id": strat["id"],
        "arch": strat["arch"],
        "label": "unknown",
        "missing": None,
    }
    arch = strat["arch"]
    rule = strat.get("sterile_if") or {}

    if arch == "additions":
        best = (ck or {}).get("best_total") or (cert or {}).get("certified_cost")
        if best is None and out:
            cost_j = read_json(out / "slp_cost.json")
            if cost_j:
                best = cost_j.get("total")
        best = best if best is not None else 56
        scored = (ck or {}).get("scored") or 0
        improvements = (ck or {}).get("improvements") or 0
        hist = (ck or {}).get("hist") or {}
        if cert:
            if cert.get("improved") or (cert.get("certified_cost") is not None and cert["certified_cost"] < 56):
                improvements = max(improvements, 1)
            improvements = max(improvements, int(cert.get("improvements") or 0))
            ch = cert.get("hist") or {}
            if ch and scored == 0:
                scored = sum(int(v) for v in ch.values())
                hist = ch
        le56 = sum(int(v) for k, v in hist.items() if str(k).isdigit() and int(k) <= 56)
        diag.update(best=best, scored=scored, improvements=improvements, le56_mass=le56)
        min_n = rule.get("min_scored") or rule.get("min_rounds", 20000)
        if best < 56:
            diag["label"] = "progress"
        elif improvements > 0 and best >= 56:
            # beat scheme baseline but not Sun-56 — still flat vs hill goal
            diag["label"] = "flat"
            diag["missing"] = f"beat scheme CSE but still {best}>=56"
        elif scored >= min_n and le56 == 0 and improvements == 0:
            diag["label"] = "sterile"
            diag["missing"] = "no mass at cost<=56; need new factorization / SLP idea"
        elif cert is not None or scored > 0:
            diag["label"] = "flat"
            diag["missing"] = "finished at/above 56"
        else:
            diag["label"] = "unrun"

    elif arch == "support":
        best = (ck or {}).get("best_support")
        if best is None and cert:
            best = cert.get("best_support") or cert.get("support")
        if best is None and sol and "u" in sol:
            best = sum(x != 0 for M in (sol["u"], sol["v"], sol["w"]) for r in M for x in r)
        if best is None:
            best = 152
        improved = (ck or {}).get("improved") or 0
        if cert:
            improved = max(improved, int(cert.get("improvements") or 0))
            if cert.get("improved"):
                improved = max(improved, 1)
        if best < 152:
            improved = max(improved, 1)
        tried = (ck or {}).get("tried") or (ck or {}).get("last_e") or 0
        diag.update(
            best=best,
            improved=improved,
            tried=tried,
            accept_rate=(ck or {}).get("accept_rate"),
        )
        min_n = rule.get("min_edits") or rule.get("min_rounds", 200000)
        if improved > 0 or best < 152:
            diag["label"] = "progress"
        elif tried >= min_n and improved == 0:
            diag["label"] = "sterile"
            diag["missing"] = "edit ball exhausted; need new seed scheme"
        elif sol is not None or cert is not None:
            diag["label"] = "flat"
            diag["missing"] = "finished at support>=152"
        elif tried > 0:
            diag["label"] = "flat"
        else:
            diag["label"] = "unrun"

    else:  # rank
        rank_cert = read_json(out / "rank_certificate.json") if out else None
        if rank_cert and rank_cert.get("exact") and rank_cert.get("best_rank", 99) < 23:
            diag["best"] = int(rank_cert["best_rank"])
            diag["label"] = "progress"
        elif rank_cert is not None:
            diag["best"] = int(rank_cert.get("best_rank") or 23)
            diag["label"] = "sterile"
            diag["missing"] = (
                f"no exact rank<23 (near_res={rank_cert.get('best_near_residual')})"
            )
        else:
            rank = len(sol["u"]) if sol and "u" in sol else None
            diag["best"] = rank if rank is not None else 23
            if rank is not None and rank < 23:
                diag["label"] = "progress"
            elif rank == 23:
                diag["label"] = "flat"
                diag["missing"] = "rank-23 only; need rank descent"
            else:
                diag["label"] = "unrun"
                diag["missing"] = "need non-random rank method / literature"

    return diag


def mark_retired(reg: dict, strat_id: str, reason: str) -> None:
    for s in reg["strategies"]:
        if s["id"] == strat_id:
            s["status"] = "retired"
            s["reason"] = reason
            break
    save_registry(reg)


def pick_next(reg: dict) -> dict | None:
    for arch in ("additions", "support", "rank"):
        for s in reg["strategies"]:
            if s["arch"] == arch and s.get("status") == "pending":
                return s
    return None


def build_cmd(strat: dict) -> list[str]:
    cmd = [sys.executable, "-u", str(ROOT / strat["tool"])]
    if strat.get("pass_positional"):
        cmd.extend(strat["pass_positional"])
    if strat.get("pass_seed_rounds"):
        cmd.extend(
            [str(strat.get("default_seed", 0)), str(strat.get("default_rounds", 1000))]
        )
    cmd.extend(strat.get("args") or [])
    return cmd


def run_strategy(strat: dict, timeout_s: float | None) -> dict:
    cmd = build_cmd(strat)
    log(f"RUN {strat['id']} arch={strat['arch']}: {' '.join(cmd)}")
    args = strat.get("args") or []
    for i, a in enumerate(args):
        if a == "--out" and i + 1 < len(args):
            (ROOT / args[i + 1]).mkdir(parents=True, exist_ok=True)
        if a in ("--log", "--checkpoint") and i + 1 < len(args):
            (ROOT / args[i + 1]).parent.mkdir(parents=True, exist_ok=True)
    for p in strat.get("pass_positional") or []:
        path = Path(p)
        tool = Path(strat["tool"]).name
        # mkdir parents for solution.json targets; mkdir the dir itself for dir-outs
        if tool in DIR_OUT_TOOLS and path.suffix != ".json":
            (ROOT / path).mkdir(parents=True, exist_ok=True)
        else:
            (ROOT / path).parent.mkdir(parents=True, exist_ok=True)

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
        elapsed = time.time() - t0
        out_tail = "\n".join((stdout or "").splitlines()[-40:])
        err_tail = "\n".join((stderr or "").splitlines()[-20:])
        if out_tail:
            log(f"stdout_tail:\n{out_tail}")
        if err_tail:
            log(f"stderr_tail:\n{err_tail}")
        return {
            "exit_code": proc.returncode,
            "elapsed_s": elapsed,
            "stdout_tail": out_tail,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        log(f"TIMEOUT after {elapsed:.0f}s for {strat['id']} — killing process group")
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except Exception:
            proc.kill()
        try:
            stdout, stderr = proc.communicate(timeout=10)
        except Exception:
            stdout, stderr = "", ""
        return {
            "exit_code": -1,
            "elapsed_s": elapsed,
            "stdout_tail": (stdout or "")[-2000:],
            "timed_out": True,
        }


def apply_diagnosis(reg: dict, strat: dict, diag: dict, st: dict) -> None:
    arch = strat["arch"]
    best = diag.get("best")
    if isinstance(best, (int, float)):
        key = arch
        cur = st["best"].get(key)
        if cur is None or best < cur:
            st["best"][key] = int(best)

    label = diag.get("label")
    if label == "sterile":
        reason = diag.get("missing") or "sterile"
        mark_retired(reg, strat["id"], reason)
        log(f"RETIRE {strat['id']}: {reason}")
    elif label == "progress":
        for s in reg["strategies"]:
            if s["id"] == strat["id"]:
                s["status"] = "active"
                s["reason"] = f"progress best={best}"
                break
        save_registry(reg)
        log(f"PROGRESS {strat['id']} best={best}")
    elif label == "flat":
        flats = (strat.get("flat_count") or 0) + 1
        for s in reg["strategies"]:
            if s["id"] == strat["id"]:
                s["flat_count"] = flats
                if flats >= 2:
                    s["status"] = "retired"
                    s["reason"] = diag.get("missing") or "flat twice"
                    log(f"RETIRE {strat['id']} after {flats} flat runs")
                break
        save_registry(reg)


def update_journal_snippet(st: dict, last: dict) -> None:
    if not JOURNAL.exists():
        return
    html = JOURNAL.read_text(encoding="utf-8")
    loop = (
        f"director cycle={st.get('cycle', 0)} · "
        f"best adds={st['best'].get('additions')} support={st['best'].get('support')} "
        f"rank={st['best'].get('rank')} · last={last.get('strategy_id')} "
        f"({last.get('label')})"
    )
    new, n = re.subn(
        r"(<div><strong>Loop</strong>)[^<]*(</div>)",
        rf"\1 {loop}\2",
        html,
        count=1,
    )
    if n:
        JOURNAL.write_text(new, encoding="utf-8")


def seed_retirements_from_disk(reg: dict) -> None:
    ck = read_json(ROOT / "logs/checkpoints/affine_checkpoint.json")
    if ck and ck.get("scored", 0) >= 20000:
        hist = ck.get("hist") or {}
        le56 = sum(int(v) for k, v in hist.items() if str(k).isdigit() and int(k) <= 56)
        if le56 == 0 and ck.get("improvements", 0) == 0:
            mark_retired(
                reg,
                "add_uv_mutate_solve_w",
                f"seeded from checkpoint scored={ck.get('scored')} le56=0",
            )
    ck = read_json(ROOT / "logs/checkpoints/support_checkpoint.json")
    if ck and ck.get("tried", 0) >= 200000 and ck.get("improved", 0) == 0:
        mark_retired(
            reg,
            "sup_stapleton_orbit_3edit",
            f"seeded from checkpoint tried={ck.get('tried')} improved=0",
        )


def refine_label_from_stdout(strat: dict, diag: dict, run_info: dict) -> None:
    tail = run_info.get("stdout_tail") or ""
    if strat["arch"] == "additions":
        if "STERILE" in tail or ("le56=0/" in tail and "improvements=0" in tail):
            diag["label"] = "sterile"
            diag["missing"] = diag.get("missing") or "STERILE/le56=0 in stdout"
        m = re.search(r"(?:best_total|certified_cost|best_cost|best)=(\d+)", tail)
        if m:
            diag["best"] = int(m.group(1))
        if "cost ->" in tail and re.search(r"cost ->\s*(\d+)", tail):
            vals = [int(x) for x in re.findall(r"cost ->\s*(\d+)", tail)]
            if vals and min(vals) < 56:
                diag["label"] = "progress"
                diag["best"] = min(vals)
        # scheme_cse done line
        m2 = re.search(r"done best=(\d+).*improvements=(\d+).*le56=(\d+)", tail)
        if m2:
            b, imp, le = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
            diag["best"] = b
            if b < 56:
                diag["label"] = "progress"
            elif le == 0:
                # no mass at/under Sun56 — sterile for hill goal even if scheme CSE improved
                diag["label"] = "sterile"
                diag["missing"] = f"scheme CSE best={b} le56=0"
            else:
                diag["label"] = "flat"
                diag["missing"] = f"scheme CSE best={b}"
    elif strat["arch"] == "support":
        m_e = re.findall(r"status e=(\d+)", tail)
        if m_e:
            diag["tried"] = max(int(x) for x in m_e)
        if re.search(r"support\s*->\s*(\d+)", tail):
            vals = [int(x) for x in re.findall(r"support\s*->\s*(\d+)", tail)]
            if vals and min(vals) < 152:
                diag["label"] = "progress"
                diag["best"] = min(vals)
        elif re.search(r"best_support=(\d+).*improved=(\d+)", tail):
            m = re.search(r"best_support=(\d+).*improved=(\d+)", tail)
            diag["best"] = int(m.group(1))
            if int(m.group(1)) < 152:
                diag["label"] = "progress"
            elif int(m.group(2)) == 0:
                diag["label"] = "sterile"
                diag["missing"] = "stdout support>=152 improved=0"
        elif "support=152" in tail and "improved=0" in tail:
            diag["label"] = "sterile"
            diag["missing"] = "stdout support=152 improved=0"
    elif strat["arch"] == "rank":
        if re.search(r"HIT.*rank=(\d+)", tail):
            ranks = [int(x) for x in re.findall(r"HIT.*?rank=(\d+)", tail)]
            if ranks and min(ranks) < 23:
                diag["label"] = "progress"
                diag["best"] = min(ranks)
        elif "rank 22" in tail or "rank 21" in tail:
            diag["label"] = "progress"
        elif "no rank-23" in tail or "no exact" in tail.lower():
            diag["label"] = "sterile"
            diag["missing"] = "flipgraph found no rank-23"
        elif "'exact': False" in tail or '"exact": false' in tail.lower() or "exact': False" in tail:
            diag["label"] = "sterile"
            diag["missing"] = "rank-drop found no exact lower rank"


def cycle_once(reg: dict, st: dict, timeout_s: float | None, dry_run: bool) -> bool:
    strat = pick_next(reg)
    if strat is None:
        log("No pending strategies left across all arches")
        return False
    if dry_run:
        log(f"DRY-RUN next={strat['id']} arch={strat['arch']} tool={strat['tool']}")
        return False

    st["cycle"] = st.get("cycle", 0) + 1
    run_info = run_strategy(strat, timeout_s=timeout_s)
    diag = diagnose_from_artifacts(strat)
    refine_label_from_stdout(strat, diag, run_info)
    # If still unrun/unknown but process finished with cert, mark flat
    if diag["label"] in ("unrun", "unknown") and run_info.get("exit_code") is not None:
        if run_info.get("timed_out"):
            diag["label"] = "flat"
            diag["missing"] = "timed out"
        else:
            diag["label"] = "flat"
            diag["missing"] = diag.get("missing") or "run finished without clear progress"

    apply_diagnosis(reg, strat, diag, st)
    event = {
        "cycle": st["cycle"],
        "strategy_id": strat["id"],
        "arch": strat["arch"],
        "label": diag["label"],
        "best": diag.get("best"),
        "missing": diag.get("missing"),
        "exit_code": run_info.get("exit_code"),
        "elapsed_s": run_info.get("elapsed_s"),
        "timed_out": run_info.get("timed_out"),
        "state_best": dict(st["best"]),
    }
    append_ledger(event)
    save_state(st)
    update_journal_snippet(st, event)
    pending_n = sum(1 for s in load_registry()["strategies"] if s.get("status") == "pending")
    log(
        f"SCOREBOARD adds={st['best'].get('additions')} support={st['best'].get('support')} "
        f"rank={st['best'].get('rank')} | pending={pending_n} | "
        f"last={strat['id']}→{diag['label']}"
    )
    log(
        f"CYCLE {st['cycle']} done id={strat['id']} label={diag['label']} "
        f"best={diag.get('best')} missing={diag.get('missing')}"
    )
    return True


def main():
    ap = argparse.ArgumentParser(description="Pure-Python RSI research director")
    ap.add_argument("--max-cycles", type=int, default=50)
    ap.add_argument("--timeout", type=float, default=3600.0, help="Per-strategy seconds")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-seed", action="store_true")
    args = ap.parse_args()

    signal.signal(signal.SIGINT, _on_sig)
    signal.signal(signal.SIGTERM, _on_sig)
    os.chdir(ROOT)

    reg = load_registry()
    st = load_state()
    if not args.no_seed:
        seed_retirements_from_disk(reg)
        reg = load_registry()

    pending = [s["id"] for s in reg["strategies"] if s.get("status") == "pending"]
    log(
        f"director start max_cycles={args.max_cycles} timeout={args.timeout}s "
        f"pending={pending}"
    )

    cycles = 0
    while cycles < args.max_cycles and not STOP:
        ok = cycle_once(reg, st, timeout_s=args.timeout, dry_run=args.dry_run)
        cycles += 1
        if not ok or args.once or args.dry_run:
            break
        reg = load_registry()

    reg = load_registry()
    pending = [s["id"] for s in reg["strategies"] if s.get("status") == "pending"]
    retired = [s["id"] for s in reg["strategies"] if s.get("status") == "retired"]
    log(f"director stop cycles={cycles} pending={pending} retired={len(retired)}")
    log(f"best so far: {st['best']}")
    if not pending:
        log("ALL STRATEGIES EXHAUSTED — add new entries to tools/strategies.json")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
