#!/usr/bin/env python3
"""Sampled triple-zero on Stapleton orbit (pair-zero exhaustive was sterile).

  python3 -u tools/support_triple_zero.py --samples 100000 --seed 3711
"""

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

from support_overnight import (  # noqa: E402
    brent_ok,
    exhaustive_zero,
    getv,
    mats,
    orbit_seeds,
    positions,
    setv,
    support,
    write_out,
)


def try_triple_zero(data, triple):
    trial = deepcopy(data)
    for name, t, i in triple:
        setv(trial, name, t, i, 0)
    if not brent_ok(*mats(trial)):
        return None
    trial, _ = exhaustive_zero(trial)
    return trial


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-triple-zero"))
    ap.add_argument("--log", type=Path, default=Path("logs/triple-zero-director.log"))
    ap.add_argument("--samples", type=int, default=100_000)
    ap.add_argument("--seed", type=int, default=3711)
    ap.add_argument("--orbit-index", type=int, default=0, help="best orbit seed index")
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    assert brent_ok(*mats(base))
    orb = orbit_seeds(base)
    orb.sort(key=lambda x: x[0])
    _, tag, seed_data = orb[args.orbit_index]
    best, _ = exhaustive_zero(deepcopy(seed_data))
    best_s = support(*mats(best))
    pos = positions(*mats(best))

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(
        f"start tag={tag} support={best_s} positions={len(pos)} "
        f"samples={args.samples} seed={args.seed}"
    )

    rng = random.Random(args.seed)
    hits = 0
    t0 = time.time()
    for n in range(args.samples):
        triple = tuple(rng.sample(pos, 3))
        trial = try_triple_zero(best, triple)
        if trial is None:
            continue
        hits += 1
        s = support(*mats(trial))
        if s < best_s:
            log(f"IMPROVED sample={n} {best_s}->{s} triple={triple}")
            best_s = s
            best = trial
            write_out(args.out, best, {"note": f"triple-zero n={n}", "improved": True})
            if best_s <= 151:
                break
        if (n + 1) % 25000 == 0:
            log(
                f"status n={n+1} best={best_s} brent_hits={hits} "
                f"elapsed={time.time()-t0:.1f}s"
            )

    elapsed = time.time() - t0
    summary = {
        "best_support": best_s,
        "improved": best_s < 152,
        "samples": args.samples,
        "brent_ok_triples": hits,
        "orbit_tag": tag,
        "elapsed_s": elapsed,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_s < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
