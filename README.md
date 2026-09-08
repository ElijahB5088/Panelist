# Panelist

Panelist is a privacy-first Android recommendation app + self-hostable backend for comics, manga, and graphic novels.

<div align="center">
  
  [![Build Status](https://img.shields.io/github/actions/workflow/status/elijahb5088/panelist/publish-image.yml?branch=main&style=for-the-badge&logo=github&label=Build)](https://github.com/elijahb5088/panelist/actions/workflows/publish-image.yml)
  [![License](https://img.shields.io/github/license/elijahb5088/panelist?style=for-the-badge&color=green)](https://github.com/elijahb5088/panelist/blob/main/LICENSE)
  [![Sponsor](https://img.shields.io/github/sponsors/elijahb5088?style=for-the-badge&logo=githubsponsors)](https://github.com/sponsors/elijahb5088)
  [![Ko-Fi](https://img.shields.io/badge/Ko--fi-F16061?logo=ko-fi&logoColor=white&style=for-the-badge)](https://ko-fi.com/elijahb5088)
  [![GitHub Stars](https://img.shields.io/github/stars/elijahb5088/panelist?style=for-the-badge&logo=github&color=yellow)](https://github.com/elijahb5088/panelist/stargazers)

</div>

## Repository layout

```
.
├── android/                 # Native Android (Kotlin + Compose)
├── server/                  # Self-hosted REST API backend
├── docs/
├── docker-compose.yml
└── .env.example
```

## Demo

Try out the API here at the demo site https://panelist-demo.elijahb5088.cc, you can also use this as a backend to test the android app.

## Quick start (self-hosted backend)

1. Copy environment file:

```bash
cp .env.example .env
```

2. Start server:

```bash
docker compose pull
docker compose up -d
```

The server image from `main` is published at `ghcr.io/elijahb5088/panelist-server:latest`. Pushes to other branches also publish branch-specific images, with branch names normalized for Docker tags (for example, `feature/auth-flow` becomes `feature-auth-flow`):

```bash
docker pull ghcr.io/elijahb5088/panelist-server:feature-auth-flow
```

Each build also receives an immutable commit SHA tag. After the first GitHub Actions publish, set the package visibility to **Public** in the repository's Packages settings so unauthenticated users can pull it.

To build the server image locally for development instead:

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build
```

3. Open API docs:

- `http://localhost:8080/docs`

### Supported deployment model

The supported deployment is one Panelist server process on one host using the
SQLite database mounted at `/app/data`. The in-process automatic sync worker,
metadata cache, rate limiting, and sync locks are process-local, so do not run
multiple server replicas or Uvicorn workers against the same database.

The PostgreSQL service in `docker-compose.yml` is reserved for future work and
is not currently supported by the application. Do not configure a PostgreSQL
`DATABASE_URL` yet; the server currently uses Python's SQLite driver directly.

Back up the SQLite volume before upgrades or host maintenance. A simple
offline backup is:

```bash
docker compose stop panelist-server
docker run --rm -v panelist_data:/data -v "$PWD":/backup alpine \
  tar czf /backup/panelist-data-backup.tgz -C /data .
docker compose start panelist-server
```

To restore, stop the server, extract the archive into the `panelist_data`
volume, then start the server and verify `/ready` and `/docs`. Keep immutable
image tags or digests so a deployment can be rolled back without changing the
database schema unexpectedly.

For production, set unique random values for `PANELIST_SECRET_KEY` and
`CREDENTIAL_ENCRYPTION_KEY`, terminate HTTPS at a trusted reverse proxy, and
set `TRUSTED_PROXY_HEADERS=true` only when that proxy overwrites forwarding
headers. The authenticated `GET /api/audit/logs` endpoint reports redacted
authentication, integration, sync, and proxy observations for the current
user. It never stores passwords, tokens, request bodies, or sensitive headers.

## Backend notes

- Provider abstraction: `TrackingProvider` with `FloppyProvider`, the
  manga-only `KitsuProvider`, and the manga-only `MALProvider`
- Floppy token is encrypted at rest on the Panelist server
- Kitsu tokens are encrypted at rest on the Panelist server
- MAL OAuth access and refresh tokens are encrypted at rest on the Panelist server
- Recommendation engine is local, content-based, and explainable
- App never talks directly to a tracker with the user token
- The Panelist server makes tracker requests. If Floppy is running on the
  Docker host, use `http://host.docker.internal:<port>` as its URL; `localhost`
  inside the app refers to the Panelist container, not the host machine.
- For HTTPS Floppy URLs, the certificate must be trusted by the Panelist
  container and match the hostname. A self-signed or private-CA certificate
  will fail TLS verification unless its CA is installed in the image.
- To enable MyAnimeList, create an API client in MyAnimeList, set `MAL_CLIENT_ID`
  and `MAL_CLIENT_SECRET` when the client has a secret,
  and register the exact `MAL_REDIRECT_URI`. Choose `MAL manga` in the Android
  profile screen, complete authorization in the browser, then refresh the
  connection and sync.
- To enable Kitsu first retreive your api token an easy way is using this command
  ```powershell
  curl.exe -X POST "https://kitsu.io/api/oauth/token" `
  -H "Content-Type: application/x-www-form-urlencoded" `
  --data-urlencode "grant_type=password" `
  --data-urlencode "username=YOUR_KITSU_EMAIL_OR_USERNAME" `
  --data-urlencode "password=YOUR_KITSU_PASSWORD"
  ```
  then paste your token into the android apps profile screen, as well as the kitsu url 'https://kitsu.io'

## Android app notes

The Android module uses:

- Kotlin
- Jetpack Compose + Material 3
- Navigation Compose
- ViewModel + repository pattern
- Retrofit API contract for Panelist server

### Android releases

Android releases are built by [`.github/workflows/android-release.yml`](.github/workflows/android-release.yml).
Create a tag with dot-separated numeric components to build and publish a signed APK, for example:

```bash
git tag v0.1.5.1
git push origin v0.1.5.1
```

Configure these repository Actions secrets once, using the same keystore for every release:

- `ANDROID_KEYSTORE_BASE64`: base64-encoded release keystore
- `ANDROID_KEYSTORE_PASSWORD`
- `ANDROID_KEY_ALIAS`
- `ANDROID_KEY_PASSWORD`

To create the keystore on Windows, run this once from a private folder and choose strong passwords:

```powershell
keytool -genkeypair -v -keystore panelist-release.jks -alias panelist -keyalg RSA -keysize 2048 -validity 10000
[Convert]::ToBase64String([IO.File]::ReadAllBytes("$PWD\panelist-release.jks")) | Set-Clipboard
```

Create the four secrets in the repository's **Settings > Secrets and variables > Actions**. Paste the clipboard contents into `ANDROID_KEYSTORE_BASE64`; use the same keystore password, alias (`panelist`), and key password entered above for the other three secrets. Keep `panelist-release.jks` and its passwords backed up securely, and never commit the keystore.

The workflow uses the GitHub run number as `versionCode`, which increases for each build, and the tag as `versionName`. Do not replace the release keystore: Android only permits updates when the application ID and signing key remain the same.

## API

See `docs/api.md`.
