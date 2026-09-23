#!/usr/bin/env python3
"""Random k=3 full triple grafts Sun base + Stapleton donor terms."""

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

from slp_w_affine import brent_ok  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=350)
    ap.add_argument("--seed", type=int, default=1130002)
    ap.add_argument("--sun", type=Path, default=Path("submissions/sun56/solution.json"))
    ap.add_argument("--donor", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-k3-graft-smoke"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    sun = json.loads(args.sun.read_text(encoding="utf-8"))
    stap = json.loads(args.donor.read_text(encoding="utf-8"))
    rank = len(sun["u"])
    rng = random.Random(args.seed)
    t0 = time.time()
    hits = 0
    for _ in range(args.samples):
        terms = rng.sample(range(rank), 3)
        data = {"u": deepcopy(sun["u"]), "v": deepcopy(sun["v"]), "w": deepcopy(sun["w"])}
        for t in terms:
            data["u"][t] = stap["u"][t][:]
            data["v"][t] = stap["v"][t][:]
            data["w"][t] = stap["w"][t][:]
        if brent_ok(data["u"], data["v"], data["w"]):
            hits += 1
    summary = {
        "k": 3,
        "samples": args.samples,
        "brent_ok": hits,
        "elapsed_s": time.time() - t0,
    }
    print(json.dumps(summary))
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
