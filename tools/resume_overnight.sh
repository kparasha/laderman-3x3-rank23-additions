#!/usr/bin/env bash
# Unattended local Agentic Director — thin wrapper around LaunchAgents.
#
# Why LaunchAgents: nohup from a Cursor agent shell gets killed when that
# shell session ends (that was the -102 / "director stopped" bug).
#
# Typical day:
#   ~2–3pm (on AC):  bash tools/resume_overnight.sh --caffeinate
#   ~7am / off AC:   bash tools/resume_overnight.sh --detach-caffeine
#
# Status dashboard: http://127.0.0.1:8765/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
LA="$ROOT/tools/launch_agents.sh"
chmod +x "$LA" 2>/dev/null || true

case "${1:-}" in
  --no-caffeinate|--without-caffeine|"")
    # Default morning-safe if no flag: keep climb alive without wake-lock
    if [[ "${1:-}" == "" ]]; then
      # preserve old default of wanting caffeine when no args — afternoon habit
      exec bash "$LA" install-caffeine
    fi
    exec bash "$LA" install-morning
    ;;
  --caffeinate)
    exec bash "$LA" install-caffeine
    ;;
  --detach-caffeine|--drop-caffeine)
    exec bash "$LA" drop-caffeine
    ;;
  --attach-caffeine)
    exec bash "$LA" install-caffeine
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
