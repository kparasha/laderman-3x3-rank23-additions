#!/usr/bin/env python3
"""Sun56: per-term two-of-three (U,V,W) sign flips preserve Brent; sample CSE cost."""

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

from slp_w_affine import brent_ok, score_uvw, write_out  # noqa: E402

# (su, sv, sw) per term — product u*v*w unchanged when exactly two factors flip.
FLIPS = (
    (1, 1, 1),
    (-1, -1, 1),
    (-1, 1, -1),
    (1, -1, -1),
)


def apply_flips(u, v, w, choices):
    u2, v2, w2 = deepcopy(u), deepcopy(v), deepcopy(w)
    for t, k in enumerate(choices):
        su, sv, sw = FLIPS[k]
        if su == -1:
            u2[t] = [-x for x in u2[t]]
        if sv == -1:
            v2[t] = [-x for x in v2[t]]
        if sw == -1:
            w2[t] = [-x for x in w2[t]]
    return u2, v2, w2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=810002)
    ap.add_argument("--cse-seeds", type=int, default=8)
    ap.add_argument("--src", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-term-pair-signflip")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    u0, v0, w0 = base["u"], base["v"], base["w"]
    rank = len(u0)
    rng = random.Random(args.seed)
    t0 = time.time()
    best = 10**9
    best_pack = None
    le56 = 0
    brent_fail = 0

    for t in range(args.trials):
        if t == 0:
            choices = [0] * rank
        else:
            choices = [rng.randint(0, 3) for _ in range(rank)]
        u, v, w = apply_flips(u0, v0, w0, choices)
        if not brent_ok(u, v, w):
            brent_fail += 1
            continue
        tot, sides = score_uvw(u, v, w, args.cse_seeds, args.seed + t * 17)
        if tot is None:
            continue
        if tot <= 56:
            le56 += 1
        if tot < best:
            best = tot
            best_pack = (u, v, w, sides, choices)

    summary = {
        "baseline_src": str(args.src),
        "trials": args.trials,
        "best_total": best,
        "le56": le56,
        "brent_fail": brent_fail,
        "improved": best < 56,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if best_pack and best < 56:
        u, v, w, sides, choices = best_pack
        write_out(
            args.out,
            u,
            v,
            w,
            sides,
            {"note": "term pair signflip", "choices_head": choices[:8]},
        )
    return 0 if best < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
