#!/usr/bin/env python3
"""Min support over Stapleton discrete orbit (transpose, S3, factor cycle)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from copy import deepcopy
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from support_overnight import brent_ok, exhaustive_zero, mats, orbit_seeds, support, write_out  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-orbit-min"))
    ap.add_argument("--log", type=Path, default=Path("logs/orbit-min-cycle68.log"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    t0 = time.time()
    orb = orbit_seeds(base)
    best_s = 10**9
    best_tag = None
    best_data = None
    rows = []

    for tag, seed, data in orb:
        if not brent_ok(*mats(data)):
            rows.append({"tag": tag, "brent": False})
            continue
        lifted, zeros = exhaustive_zero(deepcopy(data))
        s = support(*mats(lifted))
        rows.append({"tag": tag, "seed": seed, "support": s, "zeros": zeros})
        if s < best_s:
            best_s, best_tag, best_data = s, tag, lifted

    log(f"orbit_size={len(orb)} min_support={best_s} tag={best_tag}")
    improved = best_s < 152
    if improved and best_data:
        write_out(args.out, best_data, {"tag": best_tag, "improved": True})

    summary = {
        "orbit_size": len(orb),
        "min_support": best_s,
        "best_tag": best_tag,
        "improved": improved,
        "details": rows,
        "elapsed_s": time.time() - t0,
    }
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log(f"done {json.dumps({k: summary[k] for k in summary if k != 'details'})}")
    return 0 if improved else 1


if __name__ == "__main__":
    raise SystemExit(main())
