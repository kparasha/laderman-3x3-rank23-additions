#!/usr/bin/env bash
# Install/start director + dashboard as macOS LaunchAgents (survive Cursor/shell exit).
# Usage:
#   bash tools/launch_agents.sh install-morning   # director KeepAlive, no caffeinate
#   bash tools/launch_agents.sh install-caffeine  # + caffeinate -w director
#   bash tools/launch_agents.sh drop-caffeine     # unload wake-lock only
#   bash tools/launch_agents.sh status
#   bash tools/launch_agents.sh stop
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p logs/checkpoints
LABEL_DIR="$HOME/Library/LaunchAgents"
UID_NUM="$(id -u)"
DOMAIN="gui/${UID_NUM}"

DIR_LABEL="com.kparasha.agentic-director"
DASH_LABEL="com.kparasha.director-dashboard"
CAFF_LABEL="com.kparasha.director-caffeine"

PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "Missing .venv python at $PY"
  exit 1
fi

write_plist() {
  local label="$1" outfile="$2"
  shift 2
  # remaining args = ProgramArguments
  {
    echo '<?xml version="1.0" encoding="UTF-8"?>'
    echo '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">'
    echo '<plist version="1.0"><dict>'
    echo "  <key>Label</key><string>${label}</string>"
    echo '  <key>ProgramArguments</key><array>'
    for a in "$@"; do
      # escape XML specials
      local esc="$a"
      esc="${esc//&/&amp;}"
      esc="${esc//</&lt;}"
      esc="${esc//>/&gt;}"
      esc="${esc//\"/&quot;}"
      echo "    <string>${esc}</string>"
    done
    echo '  </array>'
    echo "  <key>WorkingDirectory</key><string>${ROOT}</string>"
    echo '  <key>RunAtLoad</key><true/>'
    echo '  <key>KeepAlive</key><true/>'
    echo "  <key>StandardOutPath</key><string>${ROOT}/logs/${label}.stdout</string>"
    echo "  <key>StandardErrorPath</key><string>${ROOT}/logs/${label}.stderr</string>"
    echo '  <key>EnvironmentVariables</key><dict>'
    echo "    <key>PATH</key><string>/usr/bin:/bin:/usr/sbin:/sbin:${ROOT}/.venv/bin</string>"
    echo '  </dict>'
    echo '</dict></plist>'
  } > "$outfile"
}

bootout() {
  local label="$1"
  launchctl bootout "${DOMAIN}/${label}" 2>/dev/null || true
  rm -f "${LABEL_DIR}/${label}.plist"
}

bootstrap_one() {
  local label="$1" plist="$2"
  mkdir -p "$LABEL_DIR"
  cp "$plist" "${LABEL_DIR}/${label}.plist"
  launchctl bootout "${DOMAIN}/${label}" 2>/dev/null || true
  launchctl bootstrap "$DOMAIN" "${LABEL_DIR}/${label}.plist"
  launchctl enable "${DOMAIN}/${label}" 2>/dev/null || true
  launchctl kickstart -k "${DOMAIN}/${label}" 2>/dev/null || true
  echo "loaded ${label}"
}

cmd="${1:-status}"

case "$cmd" in
  stop)
    bootout "$CAFF_LABEL"
    bootout "$DIR_LABEL"
    bootout "$DASH_LABEL"
    # also kill stragglers from old nohup starts
    pkill -f "tools/agentic_director.py" 2>/dev/null || true
    pkill -f "tools/director_dashboard.py" 2>/dev/null || true
    pkill -f "caffeinate -i -s -w" 2>/dev/null || true
    echo "stopped launch agents + stragglers"
    ;;

  drop-caffeine|detach-caffeine)
    bootout "$CAFF_LABEL"
    echo "caffeinate wake-lock unloaded; director/dashboard KeepAlive unchanged"
    ;;

  install-morning|no-caffeinate)
    # Ensure API key presence (director loads .env itself)
    if ! "$PY" -c "
from pathlib import Path
import os
ok=bool(os.environ.get('CURSOR_API_KEY','').strip())
p=Path('.env')
if p.exists():
  for line in p.read_text().splitlines():
    s=line.strip()
    if s.startswith('CURSOR_API_KEY='):
      v=s.split('=',1)[1].strip().strip('\"').strip(\"'\")
      if v: ok=True
print('ok' if ok else 'missing')
" | grep -q '^ok$'; then
      echo "CURSOR_API_KEY missing in env/.env"
      exit 1
    fi
    TMP="$(mktemp -d)"
    write_plist "$DIR_LABEL" "$TMP/${DIR_LABEL}.plist" \
      "$PY" "-u" "${ROOT}/tools/agentic_director.py" \
      "--max-cycles" "200" "--timeout" "3600" "--timeout-max" "5400"
    write_plist "$DASH_LABEL" "$TMP/${DASH_LABEL}.plist" \
      "$PY" "-u" "${ROOT}/tools/director_dashboard.py" \
      "--host" "127.0.0.1" "--port" "8765"
    bootstrap_one "$DIR_LABEL" "$TMP/${DIR_LABEL}.plist"
    bootstrap_one "$DASH_LABEL" "$TMP/${DASH_LABEL}.plist"
    bootout "$CAFF_LABEL"
    rm -rf "$TMP"
    sleep 2
    echo "dashboard http://127.0.0.1:8765/"
    launchctl print "${DOMAIN}/${DIR_LABEL}" 2>/dev/null | head -n 20 || true
    ;;

  install-caffeine|caffeinate)
    bash "$0" install-morning
    # Wait for director pid
    sleep 2
    DPID="$(pgrep -f "tools/agentic_director.py" | head -n1 || true)"
    if [[ -z "${DPID:-}" ]]; then
      echo "director not up yet; try again in a few seconds: bash tools/launch_agents.sh install-caffeine"
      exit 1
    fi
    TMP="$(mktemp -d)"
    write_plist "$CAFF_LABEL" "$TMP/${CAFF_LABEL}.plist" \
      "/usr/bin/caffeinate" "-i" "-s" "-w" "$DPID"
    # caffeinate -w exits when pid dies; KeepAlive will respawn but needs fresh pid —
    # so for caffeine we use KeepAlive false and rely on re-attach. Override plist.
    # Simpler: run caffeinate without KeepAlive (rewrite)
    python3 - <<PY
from pathlib import Path
p = Path("$TMP/${CAFF_LABEL}.plist")
t = p.read_text()
t = t.replace("<key>KeepAlive</key><true/>", "<key>KeepAlive</key><false/>")
p.write_text(t)
PY
    bootstrap_one "$CAFF_LABEL" "$TMP/${CAFF_LABEL}.plist"
    rm -rf "$TMP"
    echo "caffeinate attached to director pid $DPID (prefer AC). Drop with: bash tools/launch_agents.sh drop-caffeine"
    ;;

  status)
    echo "--- launchctl ---"
    for L in "$DIR_LABEL" "$DASH_LABEL" "$CAFF_LABEL"; do
      if launchctl print "${DOMAIN}/${L}" >/dev/null 2>&1; then
        state="$(launchctl print "${DOMAIN}/${L}" 2>/dev/null | awk '/state =/{print $3; exit}')"
        echo "$L state=$state"
      else
        echo "$L not loaded"
      fi
    done
    echo "--- processes ---"
    pgrep -fl "agentic_director|director_dashboard|caffeinate -i -s -w" || echo none
    echo "--- port 8765 ---"
    lsof -nP -iTCP:8765 -sTCP:LISTEN || echo "not listening"
    ;;

  *)
    sed -n '2,12p' "$0"
    exit 1
    ;;
esac
