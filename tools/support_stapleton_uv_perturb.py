#!/usr/bin/env python3
"""1-entry UV perturb on Stapleton + solved W; min support among Brent-ok."""

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

from slp_w_affine import brent_ok, solve_w, to_int_ternary  # noqa: E402
from support_overnight import exhaustive_zero, mats, support  # noqa: E402

TERN = (-1, 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=930002)
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-stap-uv-perturb-support")
    )
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    u0, v0 = deepcopy(base["u"]), deepcopy(base["v"])
    pos = [("u", t, i) for t, row in enumerate(u0) for i in range(9)]
    pos += [("v", t, i) for t, row in enumerate(v0) for i in range(9)]
    rng = random.Random(args.seed)
    t0 = time.time()
    brent_n = 0
    best = support(*mats(base))
    for _ in range(args.trials):
        u, v = deepcopy(u0), deepcopy(v0)
        kind, t, i = rng.choice(pos)
        mat = u if kind == "u" else v
        cur = mat[t][i]
        opts = [x for x in TERN if x != cur]
        mat[t][i] = rng.choice(opts)
        W, _ = solve_w(u, v)
        if W is None:
            continue
        w = to_int_ternary(W)
        if w is None or not brent_ok(u, v, w):
            continue
        brent_n += 1
        data = {"u": u, "v": v, "w": w}
        data, _ = exhaustive_zero(deepcopy(data))
        s = support(*mats(data))
        if s < best:
            best = s
    summary = {
        "trials": args.trials,
        "brent_ok": brent_n,
        "best_support": best,
        "improved": best < 152,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
