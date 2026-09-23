#!/usr/bin/env bash
# Unattended director — LaunchAgent wrapper.
#
# Default: Python agentic director (no Cursor SDK).
#   bash tools/resume_overnight.sh
#   bash tools/resume_overnight.sh --python
#   bash tools/resume_overnight.sh --sdk          # Cursor SDK (needs CURSOR_API_KEY)
#   bash tools/resume_overnight.sh --caffeinate   # attach wake-lock (~2–3pm on AC)
#   bash tools/resume_overnight.sh --detach-caffeine
#
# Status: http://127.0.0.1:8765/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
LA="$ROOT/tools/launch_agents.sh"
chmod +x "$LA" 2>/dev/null || true

case "${1:-}" in
  ""|--python|--no-caffeinate|--without-caffeine)
    exec bash "$LA" install-python
    ;;
  --sdk|--cursor-sdk)
    exec bash "$LA" install-sdk
    ;;
  --caffeinate|--attach-caffeine)
    exec bash "$LA" install-caffeine
    ;;
  --detach-caffeine|--drop-caffeine)
    exec bash "$LA" drop-caffeine
    ;;
  --status)
    exec bash "$LA" status
    ;;
  --stop)
    exec bash "$LA" stop
    ;;
  -h|--help)
    sed -n '2,14p' "$0"
    exit 0
    ;;
  *)
    echo "Unknown option: $1 (try --help)"
    exit 1
    ;;
esac
