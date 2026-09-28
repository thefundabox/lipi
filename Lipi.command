#!/bin/zsh
# Double-click to start Lipi and open it in your browser. Close this window (or press Ctrl+C) to stop it.
APP="$HOME/pdf-ocr-converter"
URL="http://127.0.0.1:8000"

if [ ! -x "$APP/.venv/bin/python" ]; then
  echo "Lipi isn't set up in $APP (missing .venv). Ask Claude to reinstall it."
  read -k 1 "?Press any key to close."
  exit 1
fi

if curl -s -o /dev/null --max-time 2 "$URL"; then
  echo "Lipi is already running. Opening $URL"
  open "$URL"
  exit 0
fi

cd "$APP" || exit 1
echo "Starting Lipi... (keep this window open while you use it; press Ctrl+C to stop)"
.venv/bin/python -m smart_ocr.web --port 8000 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null; echo; echo "Lipi stopped."' EXIT INT TERM

for i in {1..60}; do
  curl -s -o /dev/null --max-time 1 "$URL" && break
  sleep 0.5
done
open "$URL"
wait $SERVER
