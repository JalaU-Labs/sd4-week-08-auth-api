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

_To be completed in later steps._

## API Contract

_To be completed in later steps._

## License

MIT — see [LICENSE](LICENSE).
