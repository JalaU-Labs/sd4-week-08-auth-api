from fastapi.testclient import TestClient

from sd4_week_08_auth_api.main import app

client = TestClient(app)


def test_openapi_metadata_describes_authentication_and_tags() -> None:
    schema = client.get("/openapi.json").json()

    assert "Casdoor OIDC" in schema["info"]["description"]
    assert "Authorize" in schema["info"]["description"]
    assert {tag["name"] for tag in schema["tags"]} == {"health", "auth", "Casdoor SSO"}
    assert schema["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"


def test_openapi_models_include_descriptions_and_examples() -> None:
    schemas = client.get("/openapi.json").json()["components"]["schemas"]

    user_create = schemas["UserCreate"]["properties"]
    assert user_create["email"]["examples"] == ["alice@example.com"]
    assert user_create["username"]["description"]
    assert user_create["password"]["description"]

    login_request = schemas["LoginRequest"]["properties"]
    assert login_request["email"]["description"]
    assert login_request["password"]["examples"] == ["StrongPass123!"]

    user_public = schemas["UserPublic"]["properties"]
    assert user_public["id"]["examples"] == ["123e4567-e89b-12d3-a456-426614174000"]
    assert user_public["created_at"]["description"]

    token_response = schemas["TokenResponse"]["properties"]
    assert token_response["access_token"]["examples"] == ["opaque-session-token"]
    assert token_response["expires_in"]["examples"] == [3600]


def test_openapi_endpoints_document_summaries_and_error_responses() -> None:
    paths = client.get("/openapi.json").json()["paths"]

    register = paths["/auth/register"]["post"]
    assert register["summary"] == "Register a new user"
    assert register["description"]
    assert register["responses"]["201"]["description"]
    assert register["responses"]["409"]["description"]

    login = paths["/auth/casdoor/login"]["get"]
    assert login["responses"]["302"]["description"]
    assert login["responses"]["503"]["description"]

    callback = paths["/auth/casdoor/callback"]["get"]
    for status_code in ("401", "409", "502", "503"):
        assert callback["responses"][status_code]["description"]

    assert paths["/health"]["get"]["description"]
    assert paths["/ready"]["get"]["description"]
