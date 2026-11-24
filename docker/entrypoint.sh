#!/usr/bin/env bash
set -euo pipefail

cleanup() {
    kill -TERM "$CASDOOR_PID" "$API_PID" "$CADDY_PID" 2>/dev/null || true
    wait "$CASDOOR_PID" "$API_PID" "$CADDY_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Inject runtime credentials into Casdoor's configuration and initial data.
/usr/local/bin/inject-casdoor-config.sh

if ! python -m json.tool /app/casdoor/conf/init_data.json > /dev/null 2>&1; then
    echo "ERROR: /app/casdoor/conf/init_data.json is not valid JSON. Aborting." >&2
    exit 1
fi

python - <<'PY'
import json
import sys

with open("/app/casdoor/conf/init_data.json") as f:
    data = json.load(f)

for index, organization in enumerate(data.get("organizations", [])):
    if (
        not isinstance(organization, dict)
        or not isinstance(organization.get("name"), str)
        or not organization["name"].strip()
        or not isinstance(organization.get("owner"), str)
        or not organization["owner"].strip()
    ):
        print(
            f"ERROR: Organization at index {index} is missing a non-empty name or owner.",
            file=sys.stderr,
        )
        sys.exit(1)

for index, provider in enumerate(data.get("providers", [])):
    if (
        not isinstance(provider, dict)
        or not isinstance(provider.get("name"), str)
        or not provider["name"].strip()
        or not isinstance(provider.get("owner"), str)
        or not provider["owner"].strip()
    ):
        print(
            f"ERROR: Provider at index {index} is missing a non-empty name or owner.",
            file=sys.stderr,
        )
        sys.exit(1)

for application_index, application in enumerate(data.get("applications", [])):
    if not isinstance(application, dict):
        print(
            f"ERROR: Application at index {application_index} is invalid.",
            file=sys.stderr,
        )
        sys.exit(1)
    for provider_index, provider in enumerate(application.get("providers", [])):
        if (
            not isinstance(provider, dict)
            or not isinstance(provider.get("name"), str)
            or not provider["name"].strip()
        ):
            print(
                "ERROR: Application provider reference at "
                f"application {application_index}, index {provider_index} has no name.",
                file=sys.stderr,
            )
            sys.exit(1)
PY

/app/casdoor/casdoor &
CASDOOR_PID=$!

uvicorn sd4_week_08_auth_api.main:app --host 127.0.0.1 --port 8080 --workers 1 --no-access-log &
API_PID=$!

caddy run --config /etc/caddy/Caddyfile --adapter caddyfile &
CADDY_PID=$!

# Fail fast if any child exits.
wait -n "$CASDOOR_PID" "$API_PID" "$CADDY_PID"
