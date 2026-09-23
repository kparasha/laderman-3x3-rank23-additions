#!/usr/bin/env python3
"""Partial product sign-flip on Sun UVW + multi-seed greedy rebuild (all sides).

Hard fact targeted W-only signflip+CSE (>=57). This rebuilds U,V,W SLP schedules
on the same Brent tensor after flipping |S|≤3 products (U and W signs).

  python3 -u tools/slp_subset_signflip_rebuild.py --max-k 3 --rebuild-seeds 12
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from itertools import combinations
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_addition_search import (  # noqa: E402
    brent_ok,
    rebuild_sides_from_uvw,
    sign_flip_scheme,
    total_cost,
)
from slp_w_affine import write_out  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--max-k", type=int, default=3)
    ap.add_argument("--rebuild-seeds", type=int, default=12)
    ap.add_argument("--seed-base", type=int, default=430000)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-signflip-rebuild"))
    ap.add_argument("--log", type=Path, default=Path("logs/signflip-rebuild-director.log"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(args.src.read_text(encoding="utf-8"))
    u, v, w = data["u"], data["v"], data["w"]

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    subsets = []
    for k in range(1, args.max_k + 1):
        subsets.extend(combinations(range(23), k))
    log(f"start subsets={len(subsets)} rebuild_seeds={args.rebuild_seeds} baseline=56")

    t0 = time.time()
    best_total = 56
    best_meta = None
    best_sides = None
    best_uvw = None
    tried = 0

    for subset in subsets:
        signs = [1] * 23
        for t in subset:
            signs[t] = -1
        u2, v2, w2 = sign_flip_scheme(u, v, w, signs)
        if not brent_ok(u2, v2, w2):
            continue
        for s in range(args.rebuild_seeds):
            tried += 1
            sides = rebuild_sides_from_uvw(u2, v2, w2, seed=args.seed_base + s + len(subset) * 97)
            if sides is None:
                continue
            tot = total_cost(sides)
            if tot < best_total:
                best_total = tot
                best_meta = {"subset": subset, "rebuild_seed": s, "total": tot}
                best_sides = sides
                best_uvw = (u2, v2, w2)
                log(f"IMPROVED total={tot} subset={subset} seed={s}")

    elapsed = time.time() - t0
    improved = best_total < 56
    if improved and best_sides and best_uvw:
        u2, v2, w2 = best_uvw
        write_out(
            args.out,
            u2,
            v2,
            w2,
            best_sides,
            {**best_meta, "improved": True, "certified_cost": best_total},
        )

    summary = {
        "subsets": len(subsets),
        "rebuild_trials": tried,
        "best_total": best_total,
        "improved": improved,
        "best_meta": best_meta,
        "elapsed_s": elapsed,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if improved else 1


if __name__ == "__main__":
    raise SystemExit(main())
