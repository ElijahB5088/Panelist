# NextPanel

NextPanel is a privacy-first Android recommendation app + self-hostable backend for comics, manga, and graphic novels.

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

2. Start server:

```bash
docker compose up -d --build
```

3. Open API docs:

- `http://localhost:8080/docs`

## Backend notes

- Provider abstraction: `TrackingProvider` with initial `FloppyProvider`
- Floppy token is encrypted at rest on the NextPanel server
- Recommendation engine is local, content-based, and explainable
- App never talks directly to Floppy with user token

## Android app notes

The Android module uses:

- Kotlin
- Jetpack Compose + Material 3
- Navigation Compose
- ViewModel + repository pattern
- Retrofit API contract for NextPanel server

## API

See `docs/api.md`.
