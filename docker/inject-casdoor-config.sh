#!/usr/bin/env bash
set -euo pipefail

CASDOOR_CONFIG_PATH="${CASDOOR_CONFIG_PATH:-/app/casdoor/conf/app.conf}"
CASDOOR_INIT_DATA_TEMPLATE_PATH="${CASDOOR_INIT_DATA_TEMPLATE_PATH:-/app/casdoor/conf/init_data.json.template}"
CASDOOR_INIT_DATA_PATH="${CASDOOR_INIT_DATA_PATH:-/app/casdoor/conf/init_data.json}"

escape_sed_replacement() {
    printf '%s' "$1" | sed 's/[\/&|\\]/\\&/g'
}

replace_placeholder() {
    local file="$1"
    local placeholder="$2"
    local value="$3"
    local escaped_value

    escaped_value="$(escape_sed_replacement "$value")"
    printf 's|%s|%s|g\n' "$placeholder" "$escaped_value" | sed -i -f - "$file"
}

escape_json_string() {
    printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

if [ -n "${CASDOOR_ADMIN_PASSWORD:-}" ]; then
    replace_placeholder "$CASDOOR_CONFIG_PATH" \
        "__CASDOOR_ADMIN_PASSWORD__" "$CASDOOR_ADMIN_PASSWORD"
else
    replace_placeholder "$CASDOOR_CONFIG_PATH" "__CASDOOR_ADMIN_PASSWORD__" ""
    echo "Warning: CASDOOR_ADMIN_PASSWORD is unset or empty; Casdoor will use its welcome page." >&2
fi

cp "$CASDOOR_INIT_DATA_TEMPLATE_PATH" "$CASDOOR_INIT_DATA_PATH"
replace_placeholder "$CASDOOR_INIT_DATA_PATH" \
    "__CASDOOR_CLIENT_ID__" "$(escape_json_string "${CASDOOR_CLIENT_ID:-}")"
replace_placeholder "$CASDOOR_INIT_DATA_PATH" \
    "__CASDOOR_CLIENT_SECRET__" "$(escape_json_string "${CASDOOR_CLIENT_SECRET:-}")"
