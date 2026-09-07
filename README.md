# Panelist

Panelist is a privacy-first Android recommendation app + self-hostable backend for comics, manga, and graphic novels.

## Repository layout

```
.
├── android/                 # Native Android (Kotlin + Compose)
├── server/                  # Self-hosted REST API backend
├── docs/
├── docker-compose.yml
└── .env.example
```

## Quick start (self-hosted backend)

1. Copy environment file:

```bash
cp .env.example .env
```

Before deploying, replace `PANELIST_SECRET_KEY` and
`CREDENTIAL_ENCRYPTION_KEY` in `.env` with private random values. The example
encryption key is valid only so a fresh checkout can start; changing it later
will make previously stored tracker credentials unreadable. To generate a new
Fernet key with Python and the server dependency installed, run:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

The default SQLite database is stored in the Docker volume at
`/app/data/panelist.db`, so it persists across container restarts. The current
database layer supports SQLite only. The Compose PostgreSQL service is reserved
for future database support and is not used by the server.

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

3. Open the server homepage or API docs:

- `http://localhost:8080/` for the Panelist landing page
- `http://localhost:8080/docs` for Swagger UI
- `http://localhost:8080/redoc` for ReDoc

### Backend development

From the repository root, create a virtual environment and install the server
dependencies:

```bash
cd server
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Run the test suite from the `server` directory:

```powershell
$env:PYTHONPATH='.'; pytest -q
```

On macOS/Linux, use `PYTHONPATH=. pytest -q` instead. To run the API without
Docker, set the environment variables you need and start it with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

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
- To enable Kitsu, first retrieve an API token. This command sends the supplied
  Kitsu username and password to Kitsu's token endpoint:

  ```powershell
  curl.exe -X POST "https://kitsu.io/api/oauth/token" `
  -H "Content-Type: application/x-www-form-urlencoded" `
  --data-urlencode "grant_type=password" `
  --data-urlencode "username=YOUR_KITSU_EMAIL_OR_USERNAME" `
  --data-urlencode "password=YOUR_KITSU_PASSWORD"
  ```

  Paste the returned token into the Android app's Profile screen and use
  `https://kitsu.io` as the Kitsu server URL.

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

### Android local development

Start the backend on port 8080, then build and install the debug app from the
`android` directory:

```powershell
.\gradlew.bat :app:installDebug
```

The default emulator URL is `http://10.0.2.2:8080/`. For a physical device or
another server, pass the server URL as a Gradle property. The URL must end in
`/`:

```powershell
.\gradlew.bat :app:installDebug -PpanelistBaseUrl=http://192.168.1.20:8080/
```

Debug builds allow cleartext HTTP for local development. Release builds require
HTTPS.

## API

See [`docs/api.md`](docs/api.md) for the complete endpoint list and integration
details. A minimal authentication flow looks like this:

```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"use-a-strong-password"}'

curl -X POST http://localhost:8080/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"use-a-strong-password"}'

curl http://localhost:8080/api/me \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN'
```
