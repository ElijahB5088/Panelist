# NextPanel API (MVP)

Implemented endpoints:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `GET /api/me`
- `GET /api/profile`
- `GET /api/recommendations`
- `GET /api/recommendations/{id}`
- `POST /api/recommendations/{id}/like`
- `POST /api/recommendations/{id}/dismiss`
- `GET /api/media`
- `GET /api/media/{id}`
- `GET /api/search?q=...`
- `GET /api/library`
- `GET /api/history`
- `GET /api/ratings`
- `POST /api/integrations/floppy`
- `DELETE /api/integrations/floppy`
- `POST /api/integrations/floppy/test`
- `POST /api/sync`
- `GET /api/sync/status`

Authentication: bearer token issued by `/api/auth/login`.
