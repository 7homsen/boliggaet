# Boliggaet web service (boliggaetwebservice) – instructions for Claude

## Project
- The backend for Boliggaet, a game where the user guesses the price of current Danish property listings over five rounds, plus a mode for playing with a listing the user is physically close to. The Flutter app lives in `../boliggaetapp/`. See `docs/implementation-spec.md` for what the backend currently does.
- Two parts in one codebase:
  - **API**: a web service the app calls to get the listings for a game.
  - **Scraper**: a background worker, run on a schedule, that collects Danish property listings and keeps the database up to date.
- The game itself (rounds, guessing, revealing the price, scoring) runs in the app. The API sends each listing with its price, and the app is responsible for never showing it while the user is guessing.
- Product rule for the API: apart from the price field itself, don't send anything that gives the price away (price per m², down payment, price history, listing text that mentions the price), because the app shows the other listing data while the user is guessing.
- Python 3.13, FastAPI, PostgreSQL with PostGIS.

## Commands
Run from `boliggaetwebservice/`.
- Install dependencies: `uv sync`
- Start the local database: `docker compose up -d db`
- Apply migrations: `uv run alembic upgrade head`
- Run the API: `uv run fastapi dev app/main.py`
- Run the scraper once: `uv run python -m scraper`
- Lint: `uv run ruff check .` (must pass with no issues before a task is done)
- Format: `uv run ruff format .`
- Type check: `uv run mypy .` (must pass before a task is done)
- Test: `uv run pytest` (must pass before a task is done)

## Architecture
- **API layer** (`app/api/`): FastAPI routers. Only parse the request, call a service and return a response model. No SQL and no business logic in routers.
- **Services** (`app/services/`): the logic behind the endpoints, such as picking listings for a game. Get repositories through FastAPI dependencies, never construct them directly.
- **Repositories** (`app/repositories/`): all database access, behind small interfaces (`typing.Protocol`) so tests can use fakes.
- **Schemas** (`app/schemas/`): Pydantic request and response models. Only add fields to a response model on purpose: never return database models directly.
- **Database** (`app/db/`): SQLAlchemy 2.0 models (typed, `Mapped[...]`), session setup. Schema changes only through Alembic migrations.
- **Scraper** (`scraper/`): one module per source, each implementing the same source interface. Shared code (HTTP client with rate limiting, storing listings, marking listings as gone) lives outside the source modules. The scraper writes to the database through the same repositories as the API.
- Configuration comes from environment variables, read in one place with `pydantic-settings`. Never hard-code secrets or connection strings.

## Folder structure
```
boliggaetwebservice/
  app/
    main.py            # FastAPI app
    api/               # routers
    services/
    repositories/
    schemas/
    db/                # SQLAlchemy models, session
    config.py
  scraper/
    __main__.py        # entry point: run all enabled sources once
    sources/           # one module per source
  migrations/          # Alembic
  tests/               # mirrors app/ and scraper/
  docs/
    implementation-spec.md
    specs/<slug>/
  pyproject.toml
  docker-compose.yml
```
- Module and file names in `snake_case`.

## Code style
- Type hints everywhere; code must pass `mypy` in strict mode.
- Follow `ruff`; no unused imports, no bare `except`.
- Prefer plain functions and small classes. Use `async` for API and database code.
- Code, identifiers, comments and API field names in English. Any user-facing text the API returns (error messages shown in the app) is in Danish.
- Don't store copies of listing images: store the source's image URLs.

## Design principles
Apply SOLID, DRY, KISS and YAGNI pragmatically. When they pull in different directions, choose the simpler code.
- One responsibility per layer, as described under Architecture.
- Add a new scraping source by adding a new module that implements the source interface, not by adding `if source == ...` branches to shared code.
- Repository interfaces are worth it even with one real implementation, because the test fake is the second.
- Extract shared code the third time it appears, not before.
- Build only what the current task needs: no speculative configuration, base classes or optimisation without a measured problem.

## Scraping rules
- Respect each source's terms and `robots.txt`. Don't add a source until its use has been agreed with me and noted in its spec.
- Identify the scraper with a clear `User-Agent`, rate-limit every source (at most one request per second unless agreed otherwise), and back off on errors.
- A scraper run must be safe to repeat: upsert on the source's own listing id, never create duplicates.
- Never log or store personal data about sellers or agents beyond what the game needs.

## Implementation spec
- `docs/implementation-spec.md` is the overview of the backend as it is currently built. It is imported below so it's loaded at the start of every session: use it as context for every task.
- Keep it up to date: update it in the same change whenever you add, remove or change an endpoint, a scraping source, the data model at table level, the schedule, or how the backend is hosted.
- Keep it high-level: purpose, endpoints (what they're for and what they return, at field-group level), data model (tables and what they hold), sources and schedule, and hosting. No code.
- Describe what is built, not what is planned. Planned work lives in `docs/specs/<slug>/`.
- When an endpoint the app uses changes, say so in your report: the app in `../boliggaetapp/` may need updating too.

Current implementation spec: @docs/implementation-spec.md

## Testing
- Write unit tests for service and scraper parsing logic. Use fakes for repositories in service tests.
- Scraper parsing tests run against saved HTML/JSON fixtures in `tests/`, never against live sites.
- Test the exact shape of every endpoint's response, so fields that give away the price can't be added by accident.
- Database and migration tests run against the PostGIS container from `docker-compose.yml`.

## How I want you to work
- For larger changes, briefly explain your plan before writing code.
- Ask before adding any new dependency to `pyproject.toml`.
- Keep changes focused on the task; don't refactor unrelated code without asking.
- Run lint, type check and tests after changes and fix what you broke.
- Don't commit or push unless I ask.
