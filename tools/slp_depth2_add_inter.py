#!/usr/bin/env python3
"""Two sequential exhaustive add_inter steps (Stapleton gold @63)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from copy import deepcopy
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_exhaustive_add_inter import add_inter_at, total_cost  # noqa: E402
from slp_w_mutate import expand  # noqa: E402


def level_hits(sides):
    golds = {n: expand(sides[n])[0] for n in ("U", "V", "W")}
    out = []
    for name in ("U", "V", "W"):
        _, vs = expand(sides[name])
        n = len(vs)
        for a in range(n):
            for b in range(n):
                for sign in (1, -1):
                    cand = add_inter_at(sides[name], golds[name], a, b, sign)
                    if cand is None:
                        continue
                    trial = deepcopy(sides)
                    trial[name] = cand
                    out.append((total_cost(trial), trial))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sides", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-depth2-add-inter"))
    ap.add_argument("--log", type=Path, default=Path("logs/depth2-add-inter-cycle74.log"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    sides = json.loads(args.sides.read_text(encoding="utf-8"))
    start = total_cost(sides)

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    t0 = time.time()
    best = start
    l1 = level_hits(sides)
    log(f"level1 hits={len(l1)} start={start}")
    for t1, s1 in l1:
        if t1 < best:
            best = t1
        for t2, s2 in level_hits(s1):
            if t2 < best:
                best = t2
                log(f"level2 best={t2}")

    summary = {
        "start_total": start,
        "level1_hits": len(l1),
        "best_total": best,
        "improved": best < 56,
        "improved_stap": best < start,
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
