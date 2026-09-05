# Panelist API (MVP)

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
- `GET /api/metadata/search?q=...&limit=10`
- `GET /api/library`
- `GET /api/history`
- `GET /api/ratings`
- `POST /api/integrations/floppy`
- `DELETE /api/integrations/floppy`
- `POST /api/integrations/floppy/test`
- `POST /api/sync`
- `GET /api/sync/status`

Authentication: bearer token issued by `/api/auth/login`.

Metadata search queries Comic Vine first when `COMICVINE_API_KEY` is configured,
then Open Library and AniList. Results include `source`, `source_id`, `image_url`,
and `source_url` for attribution. Requests are made by the server, and provider
failures are isolated so an unavailable source does not fail the whole search.

Comic Vine requires an API key. Open Library asks clients to identify themselves
with `METADATA_USER_AGENT` and to cache requests; AniList is used for manga
coverage. Configure a contact address in the user agent for deployed instances.
The server caches normalized searches for 15 minutes by default, caps the cache
at 256 queries, spaces upstream requests by one second, and limits each client
to 30 searches per 60 seconds. These values can be changed with the
`METADATA_*` environment variables.
