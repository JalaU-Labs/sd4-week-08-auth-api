#!/usr/bin/env bash
set -euo pipefail

cleanup() {
    kill -TERM "$CASDOOR_PID" "$API_PID" "$CADDY_PID" 2>/dev/null || true
    wait "$CASDOOR_PID" "$API_PID" "$CADDY_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Inject runtime credentials into Casdoor's configuration and initial data.
/usr/local/bin/inject-casdoor-config.sh

/app/casdoor/casdoor &
CASDOOR_PID=$!

uvicorn sd4_week_08_auth_api.main:app --host 127.0.0.1 --port 8080 --workers 1 &
API_PID=$!

caddy run --config /etc/caddy/Caddyfile --adapter caddyfile &
CADDY_PID=$!

# Fail fast if any child exits.
wait -n "$CASDOOR_PID" "$API_PID" "$CADDY_PID"
