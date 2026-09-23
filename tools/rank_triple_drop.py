#!/usr/bin/env python3
"""Drop three products from Sun56, re-solve W, seek Brent rank 20."""

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


def drop_triple(data, triple):
    drop = set(triple)
    out = {}
    for key in ("u", "v", "w"):
        out[key] = [row[:] for t, row in enumerate(data[key]) if t not in drop]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-rank-triple-drop"))
    ap.add_argument("--log", type=Path, default=Path("logs/rank-triple-drop-director.log"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(args.src.read_text(encoding="utf-8"))
    rank = len(data["u"])
    triples = list(combinations(range(rank), 3))

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(f"start rank={rank} triples={len(triples)}")
    t0 = time.time()
    hits = []
    for triple in triples:
        d = drop_triple(data, triple)
        W, nfree = solve_w(d["u"], d["v"])
        if W is None:
            continue
        w = to_int_ternary(W)
        if w is None:
            continue
        d["w"] = w
        if brent_ok(d["u"], d["v"], d["w"]):
            hits.append((triple, len(d["u"])))
            log(f"HIT drop={triple} rank={len(d['u'])}")
            (args.out / "solution.json").write_text(
                json.dumps(d, separators=(",", ":")), encoding="utf-8"
            )
            break

    summary = {
        "start_rank": rank,
        "triples": len(triples),
        "hits": len(hits),
        "best_rank": hits[0][1] if hits else rank,
        "improved": bool(hits),
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
