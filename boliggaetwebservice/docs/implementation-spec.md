# Boliggaet web service – implementation spec

Overview of the web service as it is currently built. Updated with every change that adds, removes or changes an endpoint, a scraping source, the data model, the schedule or the hosting (see `CLAUDE.md`).

## Purpose

The web service stores current Danish property listings and serves them to the Boliggaet app. It has two parts:

- **API:** the web service the app calls to get the listings for a game. The game itself (rounds, guessing, revealing the price, scoring) runs in the app.
- **Scraper:** a background worker that runs on a schedule and keeps the listings up to date.

Nothing is built yet. The first planned work is in `docs/specs/backend-foundation/`.

## Endpoints

None yet.

## Data model

None yet.

## Scraping sources and schedule

None yet.

## Hosting

Not hosted yet.
