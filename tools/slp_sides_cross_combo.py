#!/usr/bin/env python3
"""All 2^3 mixes of Sun@56 vs Stap@63 per-side SLP certificates; min gold-valid total."""

from __future__ import annotations

import argparse
import json
import sys
import time
from itertools import product
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_scheme_sides_hill import total_cost  # noqa: E402
from slp_w_mutate import SIDES0, expand, matches_gold  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sun", type=Path, default=Path("submissions/_sun_sides0.json"))
    ap.add_argument(
        "--stap", type=Path, default=Path("submissions/director-agentic-stap63-hill-970002/sides.json")
    )
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-sides-cross-combo-118"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    sun = json.loads(args.sun.read_text(encoding="utf-8"))
    stap = json.loads(args.stap.read_text(encoding="utf-8"))
    golds = {n: expand(SIDES0[n])[0] for n in ("U", "V", "W")}
    pools = {"U": (sun["U"], stap["U"]), "V": (sun["V"], stap["V"]), "W": (sun["W"], stap["W"])}
    t0 = time.time()
    rows = []
    best = 10**9
    best_key = None
    for bits in product((0, 1), repeat=3):
        trial = {}
        for i, name in enumerate(("U", "V", "W")):
            trial[name] = pools[name][bits[i]]
        ok = all(matches_gold(trial[n], golds[n]) for n in ("U", "V", "W"))
        tot = total_cost(trial) if ok else None
        key = "".join("S" if b == 0 else "T" for b in bits)
        rows.append({"key": key, "gold_ok": ok, "total": tot})
        if ok and tot is not None and tot < best:
            best = tot
            best_key = key
    summary = {
        "combos": len(rows),
        "gold_valid": sum(1 for r in rows if r["gold_ok"]),
        "best_total": best if best < 10**9 else None,
        "best_key": best_key,
        "rows": rows,
        "improved": best < 56,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if summary["improved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
