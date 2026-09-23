#!/usr/bin/env python3
"""Exhaustive add_inter requiring ≥1 (not ≥2) final shortening."""

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
from slp_w_mutate import compact_side, expand, matches_gold, normalize_final  # noqa: E402


def add_inter_relaxed(side, gold, a, b, sign, min_improve: int = 1):
    if a == b:
        return None
    trial = deepcopy(side)
    new_idx = trial["base_dim"] + len(trial["inter"])
    trial["inter"].append((a, sign, b))
    _, vs2 = expand(trial)
    dim = len(gold[0])
    improved = 0
    new_finals = []
    for fi, f in enumerate(trial["final"]):
        target = gold[fi]
        old_len = len(f)
        found = None
        vnew = vs2[new_idx]
        if vnew == target:
            found = [(new_idx, 1)]
        elif tuple(-x for x in vnew) == target:
            found = [(new_idx, -1)]
        else:
            for i in range(len(vs2)):
                if i == new_idx:
                    continue
                for sa in (1, -1):
                    for sb in (1, -1):
                        g = tuple(sa * vnew[k] + sb * vs2[i][k] for k in range(dim))
                        if g == target:
                            found = [(new_idx, sa), (i, sb)]
                            break
                    if found:
                        break
                if found:
                    break
        if found and len(found) < old_len:
            new_finals.append(normalize_final(found))
            improved += 1
        else:
            new_finals.append(f)
    if improved < min_improve:
        return None
    trial["final"] = new_finals
    trial = compact_side(trial) or trial
    return trial if matches_gold(trial, gold) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sides", type=Path, required=True)
    ap.add_argument("--min-improve", type=int, default=1)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-relaxed-add-inter"))
    ap.add_argument("--log", type=Path, default=Path("logs/relaxed-add-inter-cycle75.log"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    sides = json.loads(args.sides.read_text(encoding="utf-8"))
    golds = {n: expand(sides[n])[0] for n in ("U", "V", "W")}
    start = total_cost(sides)

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    t0 = time.time()
    best = start
    hits = 0
    tried = 0
    for name in ("U", "V", "W"):
        _, vs = expand(sides[name])
        n = len(vs)
        for a in range(n):
            for b in range(n):
                for sign in (1, -1):
                    tried += 1
                    cand = add_inter_relaxed(
                        sides[name], golds[name], a, b, sign, args.min_improve
                    )
                    if cand is None:
                        continue
                    hits += 1
                    trial = deepcopy(sides)
                    trial[name] = cand
                    tot = total_cost(trial)
                    if tot < best:
                        best = tot
                        log(f"IMPROVED {name} total={tot}")

    summary = {
        "start_total": start,
        "best_total": best,
        "tried": tried,
        "hits": hits,
        "min_improve": args.min_improve,
        "improved": best < 56,
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
