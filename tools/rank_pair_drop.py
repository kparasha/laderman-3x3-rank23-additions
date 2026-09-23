#!/usr/bin/env python3
"""Try dropping two products from Sun56, re-solve W, seek exact Brent rank 21."""

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

from slp_w_affine import brent_ok, solve_w, to_int_ternary  # noqa: E402


def drop_pair(data, i, j):
    drop = {i, j}
    out = {}
    for key in ("u", "v", "w"):
        out[key] = [row[:] for t, row in enumerate(data[key]) if t not in drop]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-rank-pair-drop"))
    ap.add_argument("--log", type=Path, default=Path("logs/rank-pair-drop-director.log"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(args.src.read_text(encoding="utf-8"))
    rank = len(data["u"])

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(f"start rank={rank} pairs={len(list(combinations(range(rank),2)))}")
    t0 = time.time()
    hits = []
    for i, j in combinations(range(rank), 2):
        d = drop_pair(data, i, j)
        W, nfree = solve_w(d["u"], d["v"])
        if W is None:
            continue
        w = to_int_ternary(W)
        if w is None:
            continue
        d["w"] = w
        if brent_ok(d["u"], d["v"], d["w"]):
            hits.append((i, j, len(d["u"])))
            log(f"HIT drop=({i},{j}) rank={len(d['u'])} nfree={nfree}")
            (args.out / "solution.json").write_text(
                json.dumps(d, separators=(",", ":")), encoding="utf-8"
            )
            break

    summary = {
        "start_rank": rank,
        "pair_hits": len(hits),
        "best_rank": hits[0][2] if hits else rank,
        "improved": bool(hits),
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
