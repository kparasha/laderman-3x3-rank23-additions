#!/usr/bin/env python3
"""One-step bridge: can mutate/relaxed-add_inter reach the other Sun certificate?"""

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

from slp_relaxed_add_inter import add_inter_relaxed  # noqa: E402
from slp_sun_gold_bfs import scheme_key  # noqa: E402
from slp_scheme_sides_hill import total_cost  # noqa: E402
from slp_w_mutate import SIDES0, expand, matches_gold, mutate  # noqa: E402


def relaxed_neighbors(sides):
    golds = {n: expand(sides[n])[0] for n in ("U", "V", "W")}
    out = []
    for name in ("U", "V", "W"):
        _, vs = expand(sides[name])
        n = len(vs)
        for a in range(n):
            for b in range(n):
                for sign in (1, -1):
                    cand = add_inter_relaxed(sides[name], golds[name], a, b, sign, 1)
                    if cand is None:
                        continue
                    trial = deepcopy(sides)
                    trial[name] = cand
                    out.append(trial)
    return out


def mutate_sample(sides, golds, rng, tries=800):
    out = []
    for _ in range(tries):
        name = rng.choice(["U", "V", "W"])
        cand, _ = mutate(sides[name], golds[name], rng)
        if cand is None or not matches_gold(cand, golds[name]):
            continue
        trial = deepcopy(sides)
        trial[name] = cand
        out.append(trial)
    return out


def probe(sides, target_key, rng):
    golds = {n: expand(SIDES0[n])[0] for n in ("U", "V", "W")}
    hit_relaxed = hit_mut = 0
    for trial in relaxed_neighbors(sides):
        if scheme_key(trial) == target_key:
            hit_relaxed += 1
    for trial in mutate_sample(sides, golds, rng):
        if scheme_key(trial) == target_key:
            hit_mut += 1
    return hit_relaxed, hit_mut


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=770001)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-gold-bridge"))
    ap.add_argument("--log", type=Path, default=Path("logs/gold-bridge-cycle77.log"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    sides56 = {
        "U": SIDES0["U"],
        "V": SIDES0["V"],
        "W": SIDES0["W"],
    }
    sides62 = json.loads(
        Path("submissions/director-agentic-sun-cse-hill/sides.json").read_text(encoding="utf-8")
    )
    k56 = scheme_key(sides56)
    k62 = scheme_key(sides62)

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    t0 = time.time()
    rng = random.Random(args.seed)
    r56, m56 = probe(sides56, k62, rng)
    r62, m62 = probe(sides62, k56, rng)
    summary = {
        "cost56": total_cost(sides56),
        "cost62": total_cost(sides62),
        "keys_equal": k56 == k62,
        "from56_to62_relaxed": r56,
        "from56_to62_mutate800": m56,
        "from62_to56_relaxed": r62,
        "from62_to56_mutate800": m62,
        "bridge_exists": (r56 + m56 + r62 + m62) > 0,
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
