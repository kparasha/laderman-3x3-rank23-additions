#!/usr/bin/env python3
"""Sun56: random product permutations + multi-seed greedy CSE on U,V,W.

Signflip searches varied signs; UV-affine varied entries. Same tensor,
different product order can change greedy CSE totals on all three sides.

  python3 -u tools/slp_product_perm_search.py --trials 8000 --seed 660066 \\
      --out submissions/director-agentic-product-perm
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_w_affine import brent_ok, score_uvw, write_out  # noqa: E402


def permute_products(u, v, w, perm):
    return (
        [u[i][:] for i in perm],
        [v[i][:] for i in perm],
        [w[i][:] for i in perm],
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sun", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--trials", type=int, default=8000)
    ap.add_argument("--seed", type=int, default=660066)
    ap.add_argument("--cse-seeds", type=int, default=16)
    ap.add_argument("--log", type=Path, default=Path("logs/product-perm-director.log"))
    ap.add_argument(
        "--out", type=Path, default=Path("submissions/director-agentic-product-perm")
    )
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    data = json.loads(args.sun.read_text(encoding="utf-8"))
    u0, v0, w0 = data["u"], data["v"], data["w"]
    assert brent_ok(u0, v0, w0)

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    base, base_sides = score_uvw(u0, v0, w0, args.cse_seeds, args.seed)
    if base_sides is None:
        log("ERROR baseline CSE failed")
        return 2

    best = base
    best_uvw = (u0, v0, w0)
    best_sides = base_sides
    hist = Counter()
    t0 = time.time()
    log(f"start baseline_cse={base} trials={args.trials} seed={args.seed}")

    rng = random.Random(args.seed)
    rank = len(u0)
    for t in range(args.trials):
        if t == 0:
            perm = list(range(rank))
        elif t == 1:
            perm = list(reversed(range(rank)))
        else:
            perm = list(range(rank))
            rng.shuffle(perm)
        u, v, w = permute_products(u0, v0, w0, perm)
        assert brent_ok(u, v, w)
        tot, sides = score_uvw(u, v, w, args.cse_seeds, args.seed + 1000 + t)
        if sides is None:
            continue
        hist[tot] += 1
        if tot < best:
            best = tot
            best_uvw, best_sides = (u, v, w), sides
            log(f"IMPROVED t={t} perm_head={perm[:5]}... total={tot}")
            if tot < 56:
                write_out(
                    args.out,
                    u,
                    v,
                    w,
                    sides,
                    {"note": f"perm trial {t}", "improved": True, "trial": t},
                )
                break
        if (t + 1) % 2000 == 0:
            le56 = sum(v for k, v in hist.items() if k <= 56)
            log(
                f"status t={t+1} best={best} scored={sum(hist.values())} "
                f"le56={le56} min_hist={min(hist)} elapsed={time.time()-t0:.1f}s"
            )

    elapsed = time.time() - t0
    le56 = sum(v for k, v in hist.items() if k <= 56)
    summary = {
        "baseline_cse": base,
        "best_total": best,
        "improved": best < 56,
        "trials": args.trials,
        "scored": sum(hist.values()),
        "le56_count": le56,
        "hist_min": min(hist) if hist else None,
        "elapsed_s": elapsed,
    }
    log(f"done {json.dumps(summary)}")
    if best < 56 and best_uvw:
        u, v, w = best_uvw
        write_out(
            args.out,
            u,
            v,
            w,
            best_sides,
            {"note": "final best", "improved": True},
        )
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
