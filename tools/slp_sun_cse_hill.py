#!/usr/bin/env python3
"""Sun UVW: multi-seed greedy CSE (~66) then sides-hill on same gold → target 56.

SIDES0@56 is a local minimum in its component, but worse schedules on the
same (U,V,W) may connect downhill via mutate (Stapleton 64→63 precedent).

  python3 -u tools/slp_sun_cse_hill.py --cse-seeds 24 --rounds 140000 --seed 370010
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
from slp_w_affine import score_uvw  # noqa: E402
from slp_w_mutate import SIDES0, cost, expand, matches_gold, mutate, write_best  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sun", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--cse-seeds", type=int, default=24)
    ap.add_argument("--rounds", type=int, default=140_000)
    ap.add_argument("--seed", type=int, default=370010)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-sun-cse-hill"))
    ap.add_argument("--log", type=Path, default=Path("logs/sun-cse-hill-director.log"))
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    data = json.loads(args.sun.read_text(encoding="utf-8"))
    u, v, w = data["u"], data["v"], data["w"]
    lit = cost(SIDES0["U"]) + cost(SIDES0["V"]) + cost(SIDES0["W"])

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    cse_t, sides0 = score_uvw(u, v, w, args.cse_seeds, args.seed)
    if sides0 is None:
        log("ERROR CSE baseline failed")
        return 2
    log(f"CSE start total={cse_t} literature={lit} rounds={args.rounds}")

    golds = {n: expand(sides0[n])[0] for n in ("U", "V", "W")}
    cur = deepcopy(sides0)
    cur_t = total_cost(cur)
    best = deepcopy(cur)
    best_t = cur_t
    write_best(
        args.out,
        best["W"],
        best["U"],
        best["V"],
        {"note": "CSE start", "improved": False, "baseline_cse": cse_t},
    )

    rng = random.Random(args.seed + 999)
    improved = accepted = 0
    t0 = time.time()

    for r in range(1, args.rounds + 1):
        which = rng.choice(["U", "V", "W"])
        cand, op = mutate(cur[which], golds[which], rng)
        if cand is None or not matches_gold(cand, golds[which]):
            continue
        accepted += 1
        trial = deepcopy(cur)
        trial[which] = cand
        tt = total_cost(trial)
        if tt < cur_t or (tt == cur_t and rng.random() < 0.02):
            cur, cur_t = trial, tt
        if tt < best_t:
            improved += 1
            log(
                f"IMPROVED r={r} {which} {op} {best_t}->{tt} "
                f"U={cost(cur['U'])} V={cost(cur['V'])} W={cost(cur['W'])}"
            )
            best_t = tt
            best = deepcopy(cur)
            write_best(
                args.out,
                best["W"],
                best["U"],
                best["V"],
                {
                    "note": f"r={r}",
                    "improved": best_t < 56,
                    "literature": lit,
                },
            )
            if best_t < 56:
                break
        if r % 35_000 == 0:
            log(
                f"status r={r} best={best_t} cur={cur_t} imp={improved} "
                f"elapsed={time.time()-t0:.1f}s"
            )

    summary = {
        "cse_start": cse_t,
        "literature": lit,
        "best_total": best_t,
        "improved": best_t < 56,
        "improvements": improved,
        "accepted": accepted,
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_t < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
