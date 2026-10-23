#!/bin/sh
# Serve the offline Honda Freed manual and open it in the default browser.
set -eu
cd "$(dirname "$0")"
PORT="${PORT:-8000}"
URL="http://127.0.0.1:${PORT}/"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required on Linux (standard library only)." >&2
    exit 1
fi

echo "Serving $(pwd)/site at ${URL}"
python3 -m http.server "$PORT" --bind 127.0.0.1 --directory site &
PID=$!
trap 'kill "$PID" 2>/dev/null || true' INT TERM EXIT
sleep 1

if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 &
elif command -v gio >/dev/null 2>&1; then
    gio open "$URL" >/dev/null 2>&1 &
elif command -v sensible-browser >/dev/null 2>&1; then
    sensible-browser "$URL" >/dev/null 2>&1 &
else
    echo "Open ${URL} in your browser."
fi

wait "$PID"
