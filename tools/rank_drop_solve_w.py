#!/usr/bin/env python3
"""Drop one term; solve W for remaining (U,V); check Brent rank-22."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_w_affine import brent_ok, solve_w, to_int_ternary  # noqa: E402


def drop_term(data, t):
    u = [r[:] for i, r in enumerate(data["u"]) if i != t]
    v = [r[:] for i, r in enumerate(data["v"]) if i != t]
    return u, v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-rank-drop-solve-w-119"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    data = json.loads(args.src.read_text(encoding="utf-8"))
    t0 = time.time()
    hits = []
    for t in range(len(data["u"])):
        u, v = drop_term(data, t)
        W, nfree = solve_w(u, v)
        if W is None:
            continue
        w = to_int_ternary(W)
        if w is None:
            continue
        if brent_ok(u, v, w):
            hits.append({"term": t, "nfree": nfree, "rank": len(u)})
    summary = {
        "src": str(args.src),
        "trials": len(data["u"]),
        "brent_rank22": len(hits),
        "hits": hits,
        "improved": len(hits) > 0,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if summary["improved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
