#!/usr/bin/env python3
"""Two-product UV graft Stapleton→Sun, solve W, multi-seed CSE.

Single-product cross-graft scored Brent-ok but never beat 56. Pairs may hit
a new rank-23 basin with lower certified SLP.

  python3 -u tools/slp_cross_graft_pair.py --cse-seeds 10
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

from slp_w_affine import brent_ok, score_uvw, solve_w, to_int_ternary, write_out  # noqa: E402


def graft_pair_uv(base, donor, i, j):
    u = [r[:] for r in base["u"]]
    v = [r[:] for r in base["v"]]
    u[i] = donor["u"][i][:]
    v[i] = donor["v"][i][:]
    u[j] = donor["u"][j][:]
    v[j] = donor["v"][j][:]
    return {"u": u, "v": v}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sun", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument(
        "--donor", type=Path, default=Path("submissions/stapleton60/solution.json")
    )
    ap.add_argument("--cse-seeds", type=int, default=10)
    ap.add_argument("--seed", type=int, default=410001)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-cross-graft-pair"))
    ap.add_argument("--log", type=Path, default=Path("logs/cross-graft-pair-director.log"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    sun = json.loads(args.sun.read_text(encoding="utf-8"))
    donor = json.loads(args.donor.read_text(encoding="utf-8"))

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    pairs = list(combinations(range(23), 2))
    log(f"start pairs={len(pairs)} cse_seeds={args.cse_seeds}")

    t0 = time.time()
    best_total = 10**9
    best_pack = None
    best_meta = None
    brent_n = scored = 0

    for k, (i, j) in enumerate(pairs):
        base = graft_pair_uv(sun, donor, i, j)
        W, nfree = solve_w(base["u"], base["v"])
        if W is None:
            continue
        w = to_int_ternary(W)
        if w is None:
            continue
        data = {"u": base["u"], "v": base["v"], "w": w}
        if not brent_ok(data["u"], data["v"], data["w"]):
            continue
        brent_n += 1
        tot, sides = score_uvw(
            data["u"],
            data["v"],
            data["w"],
            args.cse_seeds,
            args.seed + k * 19,
        )
        if sides is None:
            continue
        scored += 1
        if tot < best_total:
            best_total = tot
            best_pack = (data, sides)
            best_meta = {"pair": (i, j), "nfree": nfree, "certified": tot}
            log(f"best_total={tot} pair=({i},{j}) brent_n={brent_n}")

    elapsed = time.time() - t0
    improved = best_pack is not None and best_total < 56
    if improved and best_pack:
        data, sides = best_pack
        write_out(
            args.out,
            data["u"],
            data["v"],
            data["w"],
            sides,
            {**best_meta, "improved": True},
        )

    summary = {
        "pairs": len(pairs),
        "brent_ok": brent_n,
        "scored": scored,
        "best_total": best_total if best_pack else None,
        "improved": improved,
        "best_meta": best_meta,
        "elapsed_s": elapsed,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if improved else 1


if __name__ == "__main__":
    raise SystemExit(main())
