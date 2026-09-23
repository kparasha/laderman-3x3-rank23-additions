#!/usr/bin/env python3
"""One-step dual-side mutate: apply U and V gold-preserving moves together.

Single-side hill/SA never changes two schedules atomically; this may reach
costs not reachable by sequential U-then-V moves on the same certificate.

  python3 -u tools/slp_sides_dual_mutate.py --trials 60000 --seed 360001 \\
      --sides submissions/_sun_sides0.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from copy import deepcopy
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_scheme_sides_hill import total_cost  # noqa: E402
from slp_w_mutate import (  # noqa: E402
    SIDES0,
    cost,
    expand,
    matches_gold,
    mutate,
    write_best,
)


def load_sides(path: Path | None):
    if path is None:
        return deepcopy({"U": SIDES0["U"], "V": SIDES0["V"], "W": SIDES0["W"]})
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sides", type=Path, default=None, help="JSON {U,V,W}; default Sun SIDES0")
    ap.add_argument("--solution", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--trials", type=int, default=60_000)
    ap.add_argument("--seed", type=int, default=360001)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-dual-mutate-sun"))
    ap.add_argument("--log", type=Path, default=Path("logs/dual-mutate-director.log"))
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    sides0 = load_sides(args.sides)
    json.loads(args.solution.read_text(encoding="utf-8"))  # sanity path exists

    golds = {n: expand(sides0[n])[0] for n in ("U", "V", "W")}
    cur = deepcopy(sides0)
    cur_t = total_cost(cur)
    best = deepcopy(cur)
    best_t = cur_t
    start_t = best_t

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(f"start total={start_t} trials={args.trials} seed={args.seed}")
    write_best(
        args.out,
        best["W"],
        best["U"],
        best["V"],
        {"note": "start", "improved": best_t < 56, "baseline_total": start_t},
    )

    rng = random.Random(args.seed)
    improved = accepted = 0
    t0 = time.time()

    for t in range(args.trials):
        trial = deepcopy(cur)
        ok = True
        for name in ("U", "V"):
            cand, _ = mutate(trial[name], golds[name], rng)
            if cand is None or not matches_gold(cand, golds[name]):
                ok = False
                break
            trial[name] = cand
        if not ok:
            continue
        accepted += 1
        tt = total_cost(trial)
        if tt <= cur_t or (tt == best_t and rng.random() < 0.04):
            cur, cur_t = trial, tt
        if tt < best_t:
            improved += 1
            log(
                f"IMPROVED t={t} {best_t}->{tt} "
                f"U={cost(trial['U'])} V={cost(trial['V'])} W={cost(trial['W'])}"
            )
            best_t = tt
            best = deepcopy(trial)
            write_best(
                args.out,
                best["W"],
                best["U"],
                best["V"],
                {"note": f"dual mutate t={t}", "improved": best_t < 56},
            )
            if best_t < 56:
                break

    elapsed = time.time() - t0
    summary = {
        "start_total": start_t,
        "best_total": best_t,
        "improved": best_t < 56,
        "improvements": improved,
        "accepted": accepted,
        "trials": args.trials,
        "elapsed_s": elapsed,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_t < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
