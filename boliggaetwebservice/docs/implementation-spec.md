# Boliggaet web service – implementation spec

Overview of the web service as it is currently built. Updated with every change that adds, removes or changes an endpoint, a scraping source, the data model, the schedule or the hosting (see `CLAUDE.md`).

## Purpose

The web service stores current Danish property listings and serves them to the Boliggaet app. It has two parts:

- **API:** the web service the app calls to get the listings for a game. The game itself (rounds, guessing, revealing the price, scoring) runs in the app.
- **Scraper:** a background worker that keeps the listings up to date. It's run manually for now.

Built from `docs/specs/backend-foundation/`.

## Endpoints

No login: both endpoints are public.

- **`GET /health`**: checks that the database can be reached. Returns `{"status": "ok"}`, or `503` with `{"status": "unavailable"}`.
- **`GET /game`**: returns 5 different active listings with at least one image, picked at random. Each listing has:
  - its id and type (`apartment` or `house`);
  - its location (lat/lng);
  - ordered image URLs and floor-plan URLs;
  - stats: energy rating, build year, renovation year, number of floors, rooms, bathrooms, toilets, square metres and listed date. Apartments also have the floor they're on; houses have no `floor` field. Stats the source doesn't provide are `null`;
  - the asking price, which the app reveals only after the guess.

  If there are fewer than 5 suitable listings it returns `503` with a Danish error message in `detail`.

## Data model

PostgreSQL with PostGIS, managed with Alembic migrations.

- **`listings`**: one row per property listing, unique on (`source`, `source_listing_id`). Holds the source and its URL, the type, the location as a PostGIS geography point with a spatial index, image and floor-plan URLs, the stats listed above, the asking price, the status (`active`, `contract_signed`, `sold`, `removed`) and `last_seen_at`. No address, description, owner costs, down payment or price history.

## Scraping sources and schedule

- The runner (`uv run python -m scraper`) runs every enabled source once. For each source it upserts the listings on (`source`, `source_listing_id`) with the status the source reports, marks the source's listings not seen for more than 2 days as `removed` (unless already `sold`), and logs how many were new, updated, deactivated and failed. A source that crashes is logged and skipped, and the run exits with a non-zero code.
- Before storing, each listing is checked: its location must be in Denmark, its price above 0 and its stats within range. A listing that fails the check, or that the database refuses, is counted as failed and skipped; the rest of the source's listings are still stored.
- If a run stores fewer than half of the source's listings that are currently listed (not `sold` or `removed`), it looks partial: nothing is marked `removed`, a warning is logged and the run exits with a non-zero code.
- Property types: villa, rækkehus, landejendom and fritidshus are houses; ejerlejlighed and andelsbolig are apartments; everything else is skipped.
- Sources use a shared HTTP client with a `User-Agent`, a rate limit (1 request per second by default) and retries with exponential backoff.
- **`sample`**: loads listings from a JSON file in the repository, for development and tests only. Off unless `SAMPLE_SOURCE_ENABLED` is set.
- No real sources yet. No schedule: the scraper is run manually.

## Hosting

Not hosted yet. Local development uses the PostGIS container from `docker-compose.yml`.
