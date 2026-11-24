#!/usr/bin/env bash
set -euo pipefail

cleanup() {
    kill -TERM "$CASDOOR_PID" "$API_PID" "$CADDY_PID" 2>/dev/null || true
    wait "$CASDOOR_PID" "$API_PID" "$CADDY_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

CASDOOR_CONFIG="/app/casdoor/conf/app.conf"

if [ -n "${CASDOOR_ADMIN_PASSWORD:-}" ]; then
    ESCAPED_PASSWORD=$(printf '%s' "$CASDOOR_ADMIN_PASSWORD" |
        sed 's/[\/&|\\]/\\&/g')
else
    ESCAPED_PASSWORD=""
    echo "Warning: CASDOOR_ADMIN_PASSWORD is unset or empty; Casdoor will use its welcome page." >&2
fi

sed -i "s|__CASDOOR_ADMIN_PASSWORD__|$ESCAPED_PASSWORD|" "$CASDOOR_CONFIG"

/app/casdoor/casdoor &
CASDOOR_PID=$!

uvicorn sd4_week_08_auth_api.main:app --host 127.0.0.1 --port 8080 --workers 1 &
API_PID=$!

caddy run --config /etc/caddy/Caddyfile --adapter caddyfile &
CADDY_PID=$!

# Fail fast if any child exits.
wait -n "$CASDOOR_PID" "$API_PID" "$CADDY_PID"
