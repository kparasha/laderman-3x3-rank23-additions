#!/usr/bin/env python3
"""Simulated-annealing support search from Stapleton (escape 152 plateau).

Prior 2/3-edit walks reset on worse support; this run accepts uphill moves with
cooling T0→Tmin so Brent-ok chains can reach support <152.

  python3 -u tools/support_sa_escape.py --steps 800000 --seed 99 \\
      --log logs/support-sa.log --out submissions/director-agentic-support-sa
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from copy import deepcopy
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
import sys

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


def apply_random_edit(data, rng, max_k=4):
    pos = positions(*mats(data))
    if len(pos) < 2:
        return None, None
    k = rng.choices([2, 3, 4], weights=[0.45, 0.4, 0.15], k=1)[0]
    k = min(k, len(pos), max_k)
    chosen = rng.sample(pos, k)
    olds = []
    for name, t, i in chosen:
        olds.append((name, t, i, getv(data, name, t, i)))
        setv(data, name, t, i, rng.choice([0, 1, -1]))
    return olds, k


def revert(data, olds):
    for name, t, i, old in olds:
        setv(data, name, t, i, old)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("submissions/stapleton60/solution.json"))
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-support-sa"))
    ap.add_argument("--steps", type=int, default=800_000)
    ap.add_argument("--seed", type=int, default=99)
    ap.add_argument("--t0", type=float, default=8.0)
    ap.add_argument("--tmin", type=float, default=0.05)
    ap.add_argument("--log", type=Path, default=Path("logs/support-sa.log"))
    ap.add_argument("--status-every", type=int, default=40000)
    args = ap.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    base = json.loads(args.src.read_text(encoding="utf-8"))
    assert brent_ok(*mats(base))

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    # Best from orbit + single-zero (cheap lift)
    orb = orbit_seeds(base)
    best = deepcopy(orb[0][2])
    best, _ = exhaustive_zero(best)
    best_s = support(*mats(best))
    cur = deepcopy(best)
    cur_s = best_s
    log(f"start best_support={best_s} steps={args.steps} seed={args.seed} T0={args.t0}")

    write_out(args.out, best, {"note": "SA seed", "improved": best_s < 152})

    rng = random.Random(args.seed)
    improved = uphill = brent_ok_n = 0
    t0 = time.time()

    for step in range(1, args.steps + 1):
        frac = step / args.steps
        T = args.t0 * (args.tmin / args.t0) ** frac
        trial = deepcopy(cur)
        olds, k = apply_random_edit(trial, rng)
        if olds is None:
            continue
        if not brent_ok(*mats(trial)):
            revert(trial, olds)
            continue
        brent_ok_n += 1
        s = support(*mats(trial))
        delta = s - cur_s
        accept = delta < 0 or (T > 1e-9 and rng.random() < math.exp(-delta / T))
        if accept:
            if delta > 0:
                uphill += 1
            cur, cur_s = trial, s
            if s < best_s:
                improved += 1
                log(f"IMPROVED step={step} k={k} {best_s}->{s} cur_walk={cur_s} T={T:.3f}")
                best_s, best = s, deepcopy(cur)
                write_out(
                    args.out,
                    best,
                    {"note": f"SA step={step}", "improved": True, "step": step},
                )
                if best_s <= 151:
                    break

        if step % args.status_every == 0:
            log(
                f"status step={step} best={best_s} cur={cur_s} T={T:.3f} "
                f"brent_ok={brent_ok_n} uphill={uphill} improved={improved} "
                f"elapsed={time.time()-t0:.1f}s"
            )

    elapsed = time.time() - t0
    summary = {
        "best_support": best_s,
        "improved": best_s < 152,
        "steps": args.steps,
        "brent_ok": brent_ok_n,
        "uphill_accepts": uphill,
        "improvements": improved,
        "elapsed_s": elapsed,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best_s < 152 else 1


if __name__ == "__main__":
    raise SystemExit(main())
