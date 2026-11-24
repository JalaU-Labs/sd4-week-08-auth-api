import json
from pathlib import Path


def test_init_data_template_providers_have_name_and_owner() -> None:
    path = Path(__file__).parent.parent / "docker" / "casdoor" / "init_data.json.template"
    data = json.loads(path.read_text())
    providers = data.get("providers", [])

    assert providers, "Providers array must not be empty"
    for provider in providers:
        assert provider.get("name"), f"Provider missing name: {provider}"
        assert provider.get("owner"), f"Provider missing owner: {provider}"

    for application in data.get("applications", []):
        for provider in application.get("providers", []):
            assert provider.get("name"), f"Application provider missing name: {provider}"


def test_init_data_template_organizations_have_name_and_owner() -> None:
    path = Path(__file__).parent.parent / "docker" / "casdoor" / "init_data.json.template"
    data = json.loads(path.read_text())
    application = next(item for item in data["applications"] if item["name"] == "sd4-auth-api")

    assert data["organizations"] == [
        {
            "owner": "admin",
            "name": "built-in",
            "displayName": "Built-in Organization",
        }
    ]
    for organization in data.get("organizations", []):
        assert organization.get("name"), f"Organization missing name: {organization}"
        assert organization.get("owner"), f"Organization missing owner: {organization}"
    assert application["organization"] == "built-in"
    assert application["redirectUris"] == ["__CASDOOR_REDIRECT_URI__"]
