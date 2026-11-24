# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.6] - 2026-11-24

### Fixed
- Added the built-in Casdoor organization and associated the SSO application with it.
- Made the Casdoor application's redirect URI dynamic and injected it from configuration.
- Routed Casdoor's token exchange to the correct internal endpoint for local and Render deployments.
- Allowed Casdoor ID tokens without `preferred_username` to derive a username from the name or email claim.
- Preserved OAuth `state` URL encoding and callback decoding.

### Changed
- Added safe callback diagnostics for token exchange, ID token validation, and user provisioning failures.
- Disabled request access logs so OAuth codes are not written to container logs.

## [0.1.5] - 2026-11-24

### Fixed
- Ensure local Compose forwards the Casdoor OIDC settings and document the Render Blueprint mappings and required dashboard secret.
- Encode the OAuth `state` sent to Casdoor and decode it before validating the callback.

### Changed
- Enrich the OpenAPI/Swagger documentation with endpoint descriptions, response details, and request and response examples.

## [0.1.4] - 2026-11-24

### Fixed
- Removed unused empty Casdoor init-data records that caused duplicate organization-key failures during startup.
- Validate generated init-data JSON and provider/organization identities before starting Casdoor.

## [0.1.3] - 2026-11-24

### Fixed
- Added a named Casdoor provider seed and startup validation for provider name and owner.

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
