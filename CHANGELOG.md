# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.3] - 2026-11-24

### Fixed
- Corrected Casdoor provider seed identities, removed empty placeholder records, and added startup validation to prevent empty-name and duplicate-key panics.

## [0.1.2] - 2026-11-24

### Added
- Casdoor OIDC SSO integration with `/auth/casdoor/login` and `/auth/casdoor/callback` endpoints.
- Just-In-Time (JIT) user provisioning for SSO users.
- `CHANGELOG.md` and finalized `README.md` documentation.

## [0.1.1] - 2026-11-24

### Fixed
- Fixed Casdoor UI subpath deployment by removing `uri strip_prefix /casdoor` from the Caddyfile.
- Added `basePath = /casdoor` to Casdoor configuration to resolve static asset loading errors.

## [0.1.0] - 2026-11-24

### Added
- Initial public authentication API (register, login, me, logout) with in-memory storage.
- Multi-stage Docker image with FastAPI, Casdoor, and Caddy.
- CI/CD pipelines for GitLab and GitHub with dual-registry publishing (GHCR and GitLab Registry).
- Render Blueprint deployment configuration.
