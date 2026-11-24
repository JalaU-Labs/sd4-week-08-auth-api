# SD4 Week 08 Auth API

Public authentication API for testing (FastAPI + Swagger UI), containerized with Docker, deployed to Render, with IAM via Casdoor.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Local Development](#local-development)
- [Production](#production)
- [Docker](#docker)
- [CI/CD](#cicd)
- [Deployment](#deployment)
- [API Contract](#api-contract)
- [License](#license)

## Features

_To be completed in later steps._

## Requirements

_To be completed in later steps._

## Local Development

_To be completed in later steps._

## Production

_To be completed in later steps._

## Docker

The production image runs the FastAPI application, Casdoor, and Caddy together. Run the production Compose file explicitly to avoid merging the development override:

```sh
docker compose -f docker-compose.yml up --build -d
docker compose -f docker-compose.yml ps
docker compose -f docker-compose.yml logs -f api
```

The service is available at `http://localhost:8080`. FastAPI's Swagger UI is at `/docs`, Casdoor is at `/casdoor/`, and the API health endpoints are `/health` and `/ready`. The production health check monitors `/health`.

Stop the production stack with:

```sh
docker compose -f docker-compose.yml down
```

For development, the default Compose command automatically merges `docker-compose.override.yml`. It bind-mounts `src/` and enables Uvicorn hot reload on port `8080`:

```sh
docker compose up --build -d
docker compose logs -f api
```

This development service runs the API directly and does not start Caddy or Casdoor. Stop it with `docker compose down`.

Casdoor's initial admin password must be supplied as a runtime secret before initial setup. The repository configuration intentionally leaves it unset; do not commit credentials.

## CI/CD

GitLab CI uses Buildah, and GitHub Actions uses Docker Buildx. Both pipelines validate and test changes before building images, and publish images to both registries for version tags.

| Event | GitLab CI | GitHub Actions |
|---|---|---|
| Pull request / merge request | lint, typecheck, test, build (no push) | same |
| Push to `main` | lint, typecheck, test, build (no push) | same |
| Tag `v*.*.*` | lint, typecheck, test, publish | same |

Published image paths:

- GHCR: `ghcr.io/jalau-labs/sd4-week-08-auth-api`
- GitLab Registry: `registry.gitlab.com/jala-university1/cohort-5/es.cssd-245.ga.t2.26.m2/sd/group-b/individual-laboratories/alejandro-botina/week-08/sd4-week-08-auth-api`

Each version tag publishes `{version}` and `{version}-{sha}` tags. The `latest` tag is published only for stable versions without a `-` suffix; pre-release versions do not update `latest`.

Configure these credentials:

- GitLab CI/CD variables: `GHCR_USER`, `GHCR_TOKEN`
- GitHub repository secrets: `GITLAB_DEPLOY_USER`, `GITLAB_DEPLOY_TOKEN`

GitHub Actions uses its built-in `GITHUB_TOKEN` to publish to GHCR.

To cut a release:

```fish
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

To consume a published image:

```fish
docker pull ghcr.io/jalau-labs/sd4-week-08-auth-api:v0.1.0
docker run --rm -p 8080:80 ghcr.io/jalau-labs/sd4-week-08-auth-api:v0.1.0
```

## Deployment

The Render service uses the Free plan and an image-backed deployment source. It consumes `ghcr.io/jalau-labs/sd4-week-08-auth-api:latest`. The Free plan sleeps after 15 minutes of inactivity; the first request after sleep may take 10 to 30 seconds while the service cold starts.

### One-time manual first deploy

1. Open https://dashboard.render.com/blueprints and click **New Blueprint Instance**.
2. Connect the GitHub repository `JalaU-Labs/sd4-week-08-auth-api` and select the `main` branch.
3. Render detects `render.yaml` and shows the `sd4-week-08-auth-api` service. When prompted for `CASDOOR_ADMIN_PASSWORD`, enter a strong password and store it in a password manager.
4. Confirm the sync. Wait for the first deploy to finish and for the health check on `/health` to turn green.
5. Open the public URL and verify:
   - `https://<service>.onrender.com/health` returns `{"status":"ok",...}`.
   - `https://<service>.onrender.com/docs` shows Swagger UI with `/auth/*` endpoints.
   - `https://<service>.onrender.com/casdoor/` shows the Casdoor login page.

### Extracting credentials for automated deploys

To configure the Deploy Hook:

1. Open the Render Dashboard.
2. Select the `sd4-week-08-auth-api` service.
3. Open **Settings** and find **Deploy Hook**.
4. Copy the Deploy Hook URL.
5. Add it to GitHub as the `RENDER_DEPLOY_HOOK` repository secret:

   ```fish
   gh secret set RENDER_DEPLOY_HOOK -R JalaU-Labs/sd4-week-08-auth-api --body "<hook-url>"
   ```

Optional API-based checks can use `RENDER_API_KEY` and `RENDER_SERVICE_ID`. Obtain `RENDER_API_KEY` from the Render Dashboard account API-key settings, and obtain `RENDER_SERVICE_ID` from the service settings or service URL. Store both as GitHub Secrets or repository variables as appropriate. The current Deploy Hook workflow requires only `RENDER_DEPLOY_HOOK`.

### Automated deploys

Pushing a stable tag `vX.Y.Z` triggers the `Deploy to Render` GitHub Actions workflow. The workflow POSTs to the Deploy Hook, and Render pulls `:latest`, which the CI pipeline publishes for the same stable tag. Pre-release tags such as `vX.Y.Z-rc.N` do not trigger deployment.

For a manual deploy, use Render Dashboard → **Manual Deploy** → **Deploy latest image**, or run the `Deploy to Render` workflow from the GitHub Actions **Run workflow** option.

### Rollback

The recommended rollback method for this lab is Render Dashboard → **Deploys**, select a previous successful deploy, and choose **Rollback**.

As an alternative, pin `render.yaml` to a specific image tag, such as `:v0.1.0`, and re-sync the Blueprint. This repository currently recommends Dashboard rollback instead of pinning the image tag.

### Secret hygiene

`CASDOOR_ADMIN_PASSWORD` is stored only in the Render Dashboard. `RENDER_DEPLOY_HOOK` is stored only as a GitHub Secret. Secret values are never committed to the repository or printed in workflow logs.

## API Contract

_To be completed in later steps._

## Casdoor SSO Integration

The API supports both its local `/auth/*` endpoints and Casdoor single sign-on using the OIDC Authorization Code flow:

```text
GET /auth/casdoor/login
  -> Casdoor sign-in and consent
  -> GET /auth/casdoor/callback?code=...&state=...
  -> validate state, exchange code, and verify the ID token
  -> provision the local user on first sign-in
  -> return a local Bearer access token
```

The ID token is verified against Casdoor's JWKS endpoint, issuer, and client ID. The resulting access token is an API session token and can be used with `/auth/me` like a token from `/auth/login`.

### Configure the client secret in Render

Set `CASDOOR_CLIENT_SECRET` in the Render service's environment settings before starting or redeploying the service. Treat it as a secret and do not commit it. The startup process injects it into Casdoor's declarative `sd4-auth-api` application; `CASDOOR_CLIENT_ID` is configured as `sd4-week-08-auth-api-client` in `render.yaml`. The issuer and callback URI are also configured there.

For a local deployment, set `CASDOOR_CLIENT_ID`, `CASDOOR_CLIENT_SECRET`, `CASDOOR_ISSUER`, and `CASDOOR_REDIRECT_URI` in the environment. These can remain empty when only running tests that mock Casdoor.

### Manually test the public flow

1. Open `https://sd4-week-08-auth-api.onrender.com/auth/casdoor/login`.
2. Sign in through Casdoor. The browser returns to the API callback and displays a JSON response containing `access_token`.
3. Use that token with the API, for example by authorizing Swagger UI at `https://sd4-week-08-auth-api.onrender.com/docs` and requesting `/auth/me`.

Users are provisioned just in time (JIT): the first successful Casdoor sign-in creates a local user using the email and preferred username claims from the verified ID token. Later sign-ins resolve the local account by email.

## License

MIT — see [LICENSE](LICENSE).
