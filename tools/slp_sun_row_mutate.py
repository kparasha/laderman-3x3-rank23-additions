#!/usr/bin/env python3
"""Sun56 + one resampled U row, solve W, score CSE (between affine and random)."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from slp_w_affine import brent_ok, score_uvw, solve_w, to_int_ternary, write_out  # noqa: E402


def random_row(rng, nnz=4):
    idx = rng.sample(range(9), nnz)
    row = [0] * 9
    for i in idx:
        row[i] = rng.choice([-1, 1])
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=550055)
    ap.add_argument("--out", type=Path, default=Path("submissions/director-agentic-sun-row-mutate"))
    ap.add_argument("--log", type=Path, default=Path("logs/sun-row-mutate-director.log"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(Path("submissions/sun56/solution.json").read_text(encoding="utf-8"))
    u0, v0, w0 = data["u"], data["v"], data["w"]

    def log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        print(line, flush=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    rng = random.Random(args.seed)
    best = 10**9
    hist = Counter()
    brent_n = scored = 0
    t0 = time.time()
    log(f"start trials={args.trials} seed={args.seed}")

    for t in range(args.trials):
        u = [r[:] for r in u0]
        ti = rng.randrange(23)
        u[ti] = random_row(rng)
        W, _ = solve_w(u, v0)
        if W is None:
            continue
        w = to_int_ternary(W)
        if w is None or not brent_ok(u, v0, w):
            continue
        brent_n += 1
        tot, sides = score_uvw(u, v0, w, 12, args.seed + t)
        if sides is None:
            continue
        scored += 1
        hist[tot] += 1
        if tot < best:
            best = tot
            log(f"IMPROVED t={t} row={ti} total={tot}")
            if tot < 56:
                write_out(args.out, u, v0, w, sides, {"improved": True, "trial": t})
                break

    summary = {
        "best_total": best if best < 10**9 else None,
        "improved": best < 56,
        "brent_ok": brent_n,
        "scored": scored,
        "le56": sum(v for k, v in hist.items() if k <= 56),
        "hist_min": min(hist) if hist else None,
        "elapsed_s": time.time() - t0,
    }
    log(f"done {json.dumps(summary)}")
    (args.out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if best < 56 else 1


if __name__ == "__main__":
    raise SystemExit(main())
