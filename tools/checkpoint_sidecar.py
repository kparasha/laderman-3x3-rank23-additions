#!/usr/bin/env python3
"""Local disk checkpoint sidecar for running overnight SLP jobs.

Does NOT touch/stop the search processes. Watches log files and writes atomic
JSON checkpoints so a reboot can resume with --resume (same seed schedule).

Network-free. Safe under low-power / sudden shutdown (last fsync'd checkpoint).

  python3 -u tools/checkpoint_sidecar.py \\
      --cse-log logs/w-cse-overnight.log \\
      --mutate-log logs/w-mutate-overnight.log \\
      --dir logs/checkpoints --every 30
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path

CSE_STATUS = re.compile(
    r"status t=(?P<t>\d+) best_total=(?P<best>\d+) valid=(?P<valid>\d+) "
    r"improvements=(?P<imp>\d+) elapsed_s=(?P<elapsed>[\d.]+)"
)
CSE_BASE = re.compile(
    r"baseline total=\d+ .*trials=(?P<trials>\d+) seed=(?P<seed>\d+)"
)
CSE_IMP = re.compile(r"IMPROVED t=(?P<t>\d+)")
CSE_DONE = re.compile(r"done best_total=(?P<best>\d+)")

MUT_STATUS = re.compile(
    r"status r=(?P<r>\d+) best_W=(?P<w>\d+) total=(?P<total>\d+) "
    r"accepted=(?P<acc>\d+) improved=(?P<imp>\d+) elapsed_s=(?P<elapsed>[\d.]+)"
)
MUT_BASE = re.compile(r"start W=\d+ .*rounds=(?P<rounds>\d+) seed=(?P<seed>\d+)")
MUT_IMP = re.compile(r"IMPROVED r=(?P<r>\d+)")
MUT_DONE = re.compile(r"done best_W=(?P<w>\d+)")


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    data = json.dumps(payload, indent=2) + "\n"
    with tmp.open("w", encoding="utf-8") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def parse_cse(text: str, path: Path) -> dict | None:
    base = None
    for m in CSE_BASE.finditer(text):
        base = m
    if base is None:
        return None
    last = None
    for m in CSE_STATUS.finditer(text):
        last = m
    improved = [int(m.group("t")) for m in CSE_IMP.finditer(text)]
    done = CSE_DONE.search(text.splitlines()[-1]) if text.strip() else None
    state = {
        "job": "slp_w_cse_overnight",
        "log": str(path),
        "seed": int(base.group("seed")),
        "trials_target": int(base.group("trials")),
        "last_t": int(last.group("t")) if last else 0,
        "best_total": int(last.group("best")) if last else 56,
        "valid": int(last.group("valid")) if last else 0,
        "improvements": int(last.group("imp")) if last else 0,
        "elapsed_s": float(last.group("elapsed")) if last else 0.0,
        "improved_trials": improved[-5:],
        "finished": bool(done),
        "resume_from_t": (int(last.group("t")) + 1) if last else 1,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    return state


def parse_mutate(text: str, path: Path) -> dict | None:
    base = None
    for m in MUT_BASE.finditer(text):
        base = m
    if base is None:
        return None
    last = None
    for m in MUT_STATUS.finditer(text):
        last = m
    improved = [int(m.group("r")) for m in MUT_IMP.finditer(text)]
    done = MUT_DONE.search(text.splitlines()[-1]) if text.strip() else None
    state = {
        "job": "slp_w_mutate",
        "log": str(path),
        "seed": int(base.group("seed")),
        "rounds_target": int(base.group("rounds")),
        "last_r": int(last.group("r")) if last else 0,
        "best_W": int(last.group("w")) if last else 30,
        "best_total": int(last.group("total")) if last else 56,
        "accepted": int(last.group("acc")) if last else 0,
        "improved": int(last.group("imp")) if last else 0,
        "elapsed_s": float(last.group("elapsed")) if last else 0.0,
        "improved_rounds": improved[-5:],
        "finished": bool(done),
        "resume_from_r": (int(last.group("r")) + 1) if last else 1,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    return state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cse-log", type=Path, default=Path("logs/w-cse-overnight.log"))
    ap.add_argument(
        "--mutate-log", type=Path, default=Path("logs/w-mutate-overnight.log")
    )
    ap.add_argument("--dir", type=Path, default=Path("logs/checkpoints"))
    ap.add_argument("--every", type=float, default=600.0,
                    help="Seconds between checkpoint writes (default 10 min)")
    ap.add_argument(
        "--once",
        action="store_true",
        help="Write one checkpoint snapshot and exit",
    )
    args = ap.parse_args()
    args.dir.mkdir(parents=True, exist_ok=True)

    last_key = None

    def tick():
        nonlocal last_key
        wrote = []
        key_parts = []
        if args.cse_log.exists():
            st = parse_cse(args.cse_log.read_text(encoding="utf-8"), args.cse_log)
            if st:
                key_parts.append(("cse", st["last_t"], st["best_total"]))
                # Only rewrite when progress or best changes
                atomic_write(args.dir / "cse_checkpoint.json", st)
                wrote.append(
                    f"cse t={st['last_t']}/{st['trials_target']} best={st['best_total']}"
                )
        if args.mutate_log.exists():
            st = parse_mutate(
                args.mutate_log.read_text(encoding="utf-8"), args.mutate_log
            )
            if st:
                key_parts.append(("mut", st["last_r"], st["best_W"]))
                atomic_write(args.dir / "mutate_checkpoint.json", st)
                wrote.append(
                    f"mutate r={st['last_r']}/{st['rounds_target']} W={st['best_W']}"
                )
        key = tuple(key_parts)
        if key == last_key and not args.once:
            return  # no status change — skip log spam (file already identical)
        last_key = key
        line = (
            f"{time.strftime('%Y-%m-%dT%H:%M:%S')} checkpoint "
            + ("; ".join(wrote) if wrote else "no logs yet")
        )
        print(line, flush=True)
        with (args.dir / "sidecar.log").open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    if args.once:
        tick()
        return 0
    while True:
        tick()
        time.sleep(args.every)


if __name__ == "__main__":
    raise SystemExit(main())
