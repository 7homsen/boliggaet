# Spec: Backend foundation

## Goal
A working web service the app can get a game from: a database of listings, one endpoint that returns 5 listings for a game, and a scraper framework that fills the database. Everything else about the game (rounds, guessing, revealing the price, scoring) happens in the app. Real scraping sources come in later specs. This spec uses a local sample-data source so everything works end to end before a real source is agreed.

## What to build

### 1. Project setup
- A Python 3.13 project in `boliggaetwebservice/` managed with `uv`, with the layout from `CLAUDE.md`.
- Dependencies: FastAPI, Uvicorn (via `fastapi[standard]`), SQLAlchemy 2.0 (async) with `asyncpg`, GeoAlchemy2, Alembic, Pydantic, `pydantic-settings`, `httpx`. Dev: `pytest`, `pytest-asyncio`, `ruff`, `mypy`.
- `docker-compose.yml` with a PostGIS database (`postgis/postgis`, Postgres 17) for local development and tests.
- `.env.example` with the settings the service reads (database URL), and `.env` in `.gitignore`.
- A `GET /health` endpoint that returns `{"status": "ok"}` and checks the database connection.

### 2. Data model
One table, **listings**, created with an Alembic migration. One row per property listing:

- **Identity:** internal id, `source` (which scraper), `source_listing_id` (the source's own id, unique together with `source`), `source_url`.
- **Type:** `apartment` or `house`.
- **Location:** a PostGIS point (`geography(Point, 4326)`, WGS84 lat/long) with a spatial (GiST) index, so nearby listings can be queried later.
- **Media:** ordered image URLs and ordered floor-plan URLs.
- **Stats:**

  | Stat | Apartment | House | Notes |
  |---|---|---|---|
  | Energy rating | ✓ | ✓ | `A2020`, `A2015`, `A2010`, `B`, `C`, `D`, `E`, `F`, `G`; empty if unknown |
  | Build year | ✓ | ✓ | |
  | Renovation year | ✓ | ✓ | Empty if not renovated or unknown |
  | Number of floors | ✓ | ✓ | For an apartment, the floors of the building |
  | Floor it's on | ✓ | – | `0` is the ground floor (stuen); negative is a basement |
  | Rooms | ✓ | ✓ | |
  | Bathrooms | ✓ | ✓ | |
  | Toilets | ✓ | ✓ | |
  | Square metres | ✓ | ✓ | Living area |
| Listed date | ✓ | ✓ | The date the listing was put on the market, according to the source, so the app can show time on the market |

- **Price:** asking price in DKK (`kontantpris`), integer.
- **Status:** one of

  | Status | Meaning | Set by |
  |---|---|---|
  | `active` | For sale on the source | Scraper |
  | `contract_signed` | The source shows "Købsaftale underskrevet" | Scraper, if the source shows it |
  | `sold` | The sale is confirmed | Scraper, if the source shows "Solgt". Later also a registry check (Datafordeler), in its own spec |
  | `removed` | Gone from the source with no sign of a sale | Scraper |

- **Last seen:** `last_seen_at`, when the scraper last found the listing on its source.

Nothing else is stored for now: no address, description text, owner costs, down payment or price history.

### 3. Game endpoint
`GET /game` returns 5 different active listings, picked at random, that have at least one image.

```json
{
  "listings": [
    {
      "id": "…",
      "type": "apartment",
      "location": { "lat": 55.6761, "lng": 12.5683 },
      "images": ["https://…", "…"],
      "floor_plans": ["https://…"],
      "stats": {
        "energy_rating": "C",
        "build_year": 1932,
        "renovation_year": 2015,
        "floors": 5,
        "floor": 3,
        "rooms": 3,
        "bathrooms": 1,
        "toilets": 1,
        "square_meters": 82,
        "listed_date": "2026-08-14"
      },
      "price": 3495000
    }
  ]
}
```

- `stats` has `floor` only when `type` is `apartment`. Stats the source doesn't provide are `null`.
- The price is included so the app can reveal it after the guess and calculate the points. The app is responsible for never showing it while the user is guessing (see `CLAUDE.md`).
- If fewer than 5 suitable listings exist: `503` with a Danish error message.
- No login: the endpoint is public.

### 4. Scraper framework
- A source interface: a source has a name and returns normalised listings (the fields from the data model).
- A runner (`python -m scraper`) that, for each enabled source:
  - fetches its listings and upserts them on (`source`, `source_listing_id`), updating `last_seen_at` and the status the source reports (`active`, `contract_signed` or `sold`). A `removed` listing that shows up again gets the status the source reports;
  - marks the source's listings that haven't been seen for more than 2 days (by `last_seen_at`) as `removed`, unless they are already `sold`. The grace period means one failed or partial run doesn't remove listings;
  - logs a summary per source: new, updated, deactivated, failed.
- Each listing is mapped to a type: villa, rækkehus, landejendom and fritidshus are houses; ejerlejlighed and andelsbolig are apartments. Everything else (grunde, projects and so on) is skipped.
- A shared HTTP client for future sources: a clear `User-Agent`, rate limiting per source (default 1 request per second), retries with backoff.
- One source, **`sample`**: loads listings from a JSON file in the repository (at least 15 listings, both apartments and houses, across different parts of Denmark, with placeholder image URLs). It's for development and tests only and is enabled through a setting, off by default.
- Running the scraper is manual for now (`uv run python -m scraper`).

## Out of scope
- A nearby-listings endpoint. The location is stored with a spatial index so it can be added later.
- Real scraping sources (Boligsiden, Boliga, agent chains, Datafordeler/BBR). Each gets its own spec once its use has been agreed.
- Storing games, guesses or scores on the server.
- Scheduling the scraper and hosting the service.
- Storing copies of images.
- Changes to the Flutter app. Connecting the app to the endpoint is a separate app spec.

## Acceptance (for reference)
- `docker compose up -d db`, `uv run alembic upgrade head` and `uv run python -m scraper` (with the sample source enabled) give a database with the sample listings, and running the scraper again creates no duplicates.
- A listing missing from the sample file keeps its status while it was last seen less than 2 days ago. After that, the next run marks it `removed`, and `GET /game` no longer returns it. Putting it back makes it `active` again. (Tests set `last_seen_at` back in time instead of waiting.)
- Listings with status `contract_signed` or `sold` in the sample file get that status, and `GET /game` never returns them.
- `GET /game` returns 5 different active listings in the shape above. Apartments have `floor` and houses don't.
- `GET /game` gives `503` when there are fewer than 5 suitable listings.
- `ruff check`, `mypy` and `pytest` pass.

## Open questions
None.

## Answers
- Only one endpoint for now, `GET /game`, returning 5 listings. Rounds, guessing and scoring are done in the app.
- Listing contents are the ones listed above. Description text and owner costs are not stored, and price history is not tracked.
- For an apartment, "number of floors" is the floors of the building.
- The stats include the date the listing was put on the market, so the app can work out the time on the market.
- Listings have a status (`active`, `contract_signed`, `sold`, `removed`) instead of an active flag. `GET /game` only picks `active` listings for now.
- Only `last_seen_at` is stored, not `first_seen_at`. A listing is marked `removed` after 2 days without being seen, not after a single missed run.
- Villa, rækkehus, landejendom and fritidshus are houses; ejerlejlighed and andelsbolig are apartments; everything else is skipped.
- It's fine that the price is visible to anyone who inspects the app's network traffic, since there's no leaderboard to cheat on. If one is added later, guessing and scoring move to the server.
