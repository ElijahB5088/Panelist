# Panelist API (MVP)

Implemented endpoints:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `GET /api/me`
- `GET /api/profile`
- `GET /api/recommendations?limit=100&media_type=comic|manga`
- `GET /api/recommendations/{id}`
- `POST /api/recommendations/{id}/like`
- `POST /api/recommendations/{id}/dismiss`
- `GET /api/media`
- `GET /api/media/{id}`
- `GET /api/search?q=...`
- `GET /api/metadata/search?q=...&limit=10`
- `GET /api/featured?surface=discover|home&limit=10`
- `GET /api/library`
- `GET /api/history`
- `GET /api/ratings`
- `POST /api/integrations/floppy`
- `GET /api/integrations/floppy/sync-settings`
- `POST /api/integrations/floppy/sync-settings`
- `DELETE /api/integrations/floppy`
- `POST /api/integrations/floppy/test`
- `POST /api/integrations/kitsu`
- `DELETE /api/integrations/kitsu`
- `POST /api/integrations/kitsu/test`
- `POST /api/integrations/mal/authorize`
- `GET /api/integrations/mal/callback`
- `DELETE /api/integrations/mal`
- `POST /api/sync`
- `GET /api/sync/status`

Floppy credentials are encrypted at rest and are never returned by the API.
Automatic Floppy sync is disabled when a credential is connected or replaced.
Authenticated clients can enable it with the sync settings endpoint and choose
an interval from 15 minutes through 7 days. The single Panelist server process
runs due syncs in the background; failures remain recorded in the integration
status and are retried on the next interval.

Authentication: bearer token issued by `/api/auth/login`.

MAL integration uses server-managed OAuth with plain PKCE. Set `MAL_CLIENT_ID`,
`MAL_CLIENT_SECRET` when provided by MyAnimeList, and register `MAL_REDIRECT_URI`.
The callback stores encrypted
access and refresh tokens; Panelist imports only the user's manga list.

Kitsu sync uses the Kitsu API base URL (normally `https://kitsu.io`) and a
Kitsu bearer token. Only manga library entries are imported; anime entries are
ignored. The server stores the token encrypted and makes all Kitsu requests on
behalf of the Android app.

Metadata search queries Comic Vine first when `COMICVINE_API_KEY` is configured,
then Open Library and AniList. Results include `source`, `source_id`, `image_url`,
and `source_url` for attribution. Requests are made by the server, and provider
failures are isolated so an unavailable source does not fail the whole search.

Metron is an optional comic-series provider. Configure `METRON_API_TOKEN` with a
read-only Metron API token. `METRON_API_URL` overrides the default
`https://metron.cloud/api`. Metron is skipped when no token is configured, and
provider failures remain isolated.

Comic Vine requires an API key. Open Library asks clients to identify themselves
with `METADATA_USER_AGENT` and to cache requests; AniList is used for manga
coverage. Configure a contact address in the user agent for deployed instances.
The server caches normalized searches for 15 minutes by default, caps the cache
at 256 queries, spaces upstream requests by one second, and limits each client
to 30 searches per 60 seconds. These values can be changed with the
`METADATA_*` environment variables.

`GET /api/featured?surface=discover|home&limit=10` returns curated, source-backed
presets assembled from configured metadata providers. It never returns local
demo records. When providers return no results, clients receive an empty list
or show their error state.

`GET /api/recommendations` includes `source`, `source_id`, `image_url`, and
`source_url` when provenance is available. Users without personalized results
receive source-backed featured picks with `why: "Featured pick"`.
The optional `media_type` parameter filters recommendations before the limit is
applied and accepts `comic` or `manga`.
