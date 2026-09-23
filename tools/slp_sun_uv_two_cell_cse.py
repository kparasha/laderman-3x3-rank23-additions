#!/usr/bin/env python3
"""Two simultaneous UV cell changes on Sun56 + solve W; min CSE total."""

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

from slp_w_affine import brent_ok, score_uvw, solve_w, to_int_ternary  # noqa: E402

TERN = (-1, 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=1300)
    ap.add_argument("--seed", type=int, default=1270002)
    ap.add_argument("--cse-seeds", type=int, default=6)
    ap.add_argument("--src", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-sun-uv2-cse-127"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    u0, v0 = deepcopy(base["u"]), deepcopy(base["v"])
    pos = [("u", t, i) for t, row in enumerate(u0) for i in range(9)]
    pos += [("v", t, i) for t, row in enumerate(v0) for i in range(9)]
    rng = random.Random(args.seed)
    t0 = time.time()
    brent_n = 0
    best = 10**9
    for j in range(args.trials):
        u, v = deepcopy(u0), deepcopy(v0)
        (k1, t1, i1), (k2, t2, i2) = rng.sample(pos, 2)
        for kind, t, i in ((k1, t1, i1), (k2, t2, i2)):
            mat = u if kind == "u" else v
            cur = mat[t][i]
            mat[t][i] = rng.choice([x for x in TERN if x != cur])
        W, _ = solve_w(u, v)
        if W is None:
            continue
        w = to_int_ternary(W)
        if w is None or not brent_ok(u, v, w):
            continue
        brent_n += 1
        tot, _ = score_uvw(u, v, w, args.cse_seeds, args.seed + j)
        if tot is not None:
            best = min(best, tot)
    summary = {
        "trials": args.trials,
        "brent_ok": brent_n,
        "best_cse": best if brent_n else None,
        "improved": brent_n > 0 and best < 56,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if summary["improved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
