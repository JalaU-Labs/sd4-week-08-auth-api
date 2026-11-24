import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT_DATA_TEMPLATE = ROOT / "docker/casdoor/init_data.json.template"
CONFIG_INJECTOR = ROOT / "docker/inject-casdoor-config.sh"


def test_init_data_template_defines_casdoor_oidc_application() -> None:
    init_data = json.loads(INIT_DATA_TEMPLATE.read_text())
    application = next(item for item in init_data["applications"] if item["name"] == "sd4-auth-api")

    assert application["organization"] == "built-in"
    assert application["clientId"] == "__CASDOOR_CLIENT_ID__"
    assert application["clientSecret"] == "__CASDOOR_CLIENT_SECRET__"
    assert application["redirectUris"] == ["__CASDOOR_REDIRECT_URI__"]
    assert application["grantTypes"] == ["authorization_code"]
    assert application["tokenFormat"] == "JWT"
    assert application["isEnabled"] is True


def test_config_injector_substitutes_credentials_without_printing_them(
    tmp_path: Path,
) -> None:
    casdoor_config = tmp_path / "app.conf"
    init_data_template = tmp_path / "init_data.json.template"
    init_data_output = tmp_path / "init_data.json"
    casdoor_config.write_text("initAdminPassword = __CASDOOR_ADMIN_PASSWORD__\n")
    init_data_template.write_text(
        json.dumps(
            {
                "clientId": "__CASDOOR_CLIENT_ID__",
                "clientSecret": "__CASDOOR_CLIENT_SECRET__",
            }
        )
    )
    admin_password = "admin/with&special|chars\\"
    client_secret = 'secret/with&special|chars\\"'
    environment = {
        **os.environ,
        "CASDOOR_ADMIN_PASSWORD": admin_password,
        "CASDOOR_CLIENT_ID": "sd4-week-08-auth-api-client",
        "CASDOOR_CLIENT_SECRET": client_secret,
        "CASDOOR_CONFIG_PATH": str(casdoor_config),
        "CASDOOR_INIT_DATA_TEMPLATE_PATH": str(init_data_template),
        "CASDOOR_INIT_DATA_PATH": str(init_data_output),
    }

    result = subprocess.run(
        [str(CONFIG_INJECTOR)],
        check=True,
        capture_output=True,
        env=environment,
        text=True,
    )
    rendered_config = casdoor_config.read_text()
    rendered_init_data = json.loads(init_data_output.read_text())

    assert rendered_config == f"initAdminPassword = {admin_password}\n"
    assert rendered_init_data == {
        "clientId": "sd4-week-08-auth-api-client",
        "clientSecret": client_secret,
    }
    assert admin_password not in result.stdout + result.stderr
    assert client_secret not in result.stdout + result.stderr
