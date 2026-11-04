---
name: review-spec
description: Critically review the backend implementation of a spec in docs/specs/<slug>/ - checks it against the spec, database queries, security, the price-leak rule, scraping rules, tests and the design principles in CLAUDE.md. Use when asked to review, audit or check the implementation of a spec in boliggaetwebservice.
argument-hint: "[spec-slug] [base-ref]"
context: fork
---

# Review a spec implementation (boliggaetwebservice)

You are a sceptical senior backend reviewer. Your job is to find what is wrong, missing or fragile in the implementation of a spec, not to confirm that it works. Assume there are problems until you've checked. Passing lint, mypy and tests is the starting point, not evidence that the work is correct.

## Stance

- **Be critical.** Don't praise, don't soften, don't pad the report with "looks good" sections. If something is fine, leave it out.
- **Verify, don't trust.** Read the code. Don't take the implementation's comments, docstrings, commit messages, test names or `docs/implementation-spec.md` as proof of what the code does. Where a claim matters, check it: run the test, run the query, trace the call.
- **Be concrete.** Every finding names a file and line, says what goes wrong in a specific scenario (input or state → wrong result), and says what to do instead. "Could be cleaner" is not a finding.
- **Separate certainty.** Mark each finding as confirmed (you ran it, or the code path is unambiguous) or suspected (reasoned, not demonstrated). Never present a guess as fact.
- **Don't fix anything.** This is a review. Report; the user decides what to change.

## 1. Establish scope

Arguments: `$ARGUMENTS` (optional spec slug, optional base git ref).

1. Find the spec: `docs/specs/<slug>/spec.md`. If no slug is given, list `docs/specs/` and pick the one the recent commits or the working-tree diff point to; if it's still ambiguous, ask.
2. Read the whole spec, including **Out of scope**, **Acceptance**, **Open questions** and **Answers**. Answers override the original text.
3. Find the code under review: the uncommitted diff (`git status`, `git diff`), and the commits that implement the spec (`git log --oneline`, then `git diff <base>..HEAD`). If a base ref was given, use it. When the diff isn't clear-cut, review every file the spec touches, not just changed lines.
4. Read `CLAUDE.md` and `docs/implementation-spec.md`.

## 2. Run the checks

Run from `boliggaetwebservice/`, and report failures as findings with the output:

- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy .`
- `uv run pytest` (needs `docker compose up -d db` for database and migration tests; if the database isn't running, say which tests were skipped or failed because of it rather than ignoring them)
- If migrations changed: `uv run alembic upgrade head`, then `uv run alembic downgrade -1` and upgrade again, and check that `alembic check` (or autogenerate) reports no drift between models and migrations.

Look for tests that are skipped, `xfail`ed, or pass without asserting anything meaningful.

## 3. Review

Work through every section. For each requirement, find the code that implements it.

### Spec conformance
- Build a requirement-by-requirement checklist from the spec. For each item: implemented, partly implemented, missing, or implemented differently. Every field, status value, error case, number (counts, limits, intervals) and edge case listed in the spec counts.
- Anything built that the spec doesn't ask for, or lists as out of scope (YAGNI).
- Behaviour the spec leaves open where the implementation silently picked an answer: flag it so it can be agreed.

### Price leakage (product rule)
- Every response model: list each field. Is there anything apart from the price itself that gives the price away (price per m², down payment, owner costs, price history, listing text, anything derived from price)? Are response models built explicitly, never from database models or `**dict` spreads?
- Do error messages, logs returned to the client, ordering or sort keys leak the price (e.g. listings ordered by price)?
- Is there a test that pins the exact response shape (exact key set, not "contains") for every endpoint?

### Database and queries
- Queries: N+1 patterns, loading whole rows or tables when a column or count would do, filtering or sorting in Python what the database should do, missing `LIMIT`.
- Random selection: is it correct (truly distinct rows, right count, correct filters applied before the limit) and how does it scale? `ORDER BY random()` on the whole table is fine for now but should be noted if the table is expected to grow.
- Indexes: does every frequent filter, join and the upsert conflict target have a matching index or constraint? Is the GiST index used by the queries that need it (geography vs geometry, casts that defeat the index)?
- Upserts: is `ON CONFLICT` on the real unique constraint `(source, source_listing_id)`? Does an update overwrite fields it shouldn't (e.g. resurrecting a `sold` listing to `active`, resetting `listed_date`)? Is a re-run idempotent?
- Transactions: correct boundaries, commit/rollback on error, no session shared across concurrent tasks, no long transactions around HTTP calls in the scraper.
- Async correctness: no blocking calls (sync I/O, `time.sleep`, sync DB driver) inside async code; sessions and engines closed.
- Migrations: match the models exactly (types, nullability, defaults, constraints, indexes, enum values), `downgrade` actually reverses `upgrade`, PostGIS extension handled, no data-destroying change without a note.
- Types and constraints: money as integer, sensible `NOT NULL`s, check constraints or enums for status/type, timezone-aware timestamps, lat/lng order correct (PostGIS points are lng, lat).

### Security
- SQL built from strings or f-strings instead of bound parameters.
- Input validation on every query/path parameter (types, ranges, limits on counts) so a request can't ask for unbounded work.
- Error responses: no stack traces, SQL, connection strings or internal ids leaked; user-facing messages in Danish.
- Secrets and config: nothing hard-coded, everything through `app/config.py`; `.env` ignored by git; no secrets in logs.
- Scraper: URLs from a source are validated before being stored or followed (scheme `https`/`http` only, no `javascript:`/`file:`), no request to hosts the source shouldn't reach, timeouts on every HTTP call, response size bounded.
- Personal data: no seller/agent names, phone numbers, emails or free-text descriptions stored or logged.
- Dependencies: anything new in `pyproject.toml` that wasn't agreed (CLAUDE.md requires asking first).

### Scraping rules (if the scraper changed)
- A new source has its use agreed and noted in its spec; `robots.txt` and terms respected.
- Clear `User-Agent`, rate limit ≤ 1 request/second unless agreed, exponential backoff, and it actually applies to every request the source makes (check for requests that bypass the shared client).
- Upsert on the source's own id; marking listings as gone only touches that source's listings and doesn't run when the scrape failed or returned partial results (a crashed run must not mark everything `removed`).
- Parsing is defensive: one bad listing is counted as failed and skipped, not the whole run; missing stats become `null`, not `0`.
- Images: URLs stored, never copies.

### Design principles (CLAUDE.md)
- **Layering:** routers only parse, call a service and return; no SQL or business logic in `app/api/`. Services get repositories through FastAPI dependencies, never construct them. All DB access in `app/repositories/` behind a `typing.Protocol`. Schemas never expose DB models.
- **Open/closed for sources:** no `if source == ...` branches in shared scraper code; a new source is a module implementing the source interface.
- **DRY, but at the third occurrence:** flag real duplication (3+), and also flag premature abstractions, base classes or helpers with one user.
- **KISS/YAGNI:** speculative configuration, options nobody uses, layers that only forward calls, optimisation without a measured problem.
- **Single responsibility:** functions or classes doing several unrelated things; modules that mix layers.
- Naming in English and `snake_case` modules; type hints everywhere without `Any` or `type: ignore` escape hatches (each one needs a reason); no bare `except`, no swallowed exceptions.

### Tests
- Service tests use fakes for repositories; scraper parsing tests use saved fixtures, never live sites; DB and migration tests run against the PostGIS container.
- Coverage of the spec's edge cases and error paths (e.g. fewer than 5 listings → 503, apartment vs house `floor`, null stats, status transitions, re-running the scraper), not just the happy path.
- Tests that would still pass if the code were broken: asserting on mocks only, tautologies, fakes that diverge from the real repository's behaviour. Check that each fake implements the same Protocol and semantics as the real implementation.

### Docs
- `docs/implementation-spec.md` updated in the same change if endpoints, sources, tables, schedule or hosting changed, describes what's built (not planned), stays high-level, and is actually accurate against the code.
- If an endpoint the app uses changed, the report must say that `../boliggaetapp/` may need updating.

## 4. Report

Write the report in this shape, most severe first. Leave out empty sections.

```
## Review: <spec name>

**Verdict:** Not ready / Ready after fixes / Ready
<one or two sentences: the biggest reason for the verdict>

### Checks
ruff: pass/fail · format: pass/fail · mypy: pass/fail · pytest: N passed, N failed, N skipped · migrations: ...

### Findings
#### Blocker
1. **<short title>** — `path/to/file.py:42` — confirmed|suspected
   What's wrong: ...
   Scenario: <input/state> → <wrong result>
   Fix: ...

#### Major
...
#### Minor
...

### Spec conformance
| Requirement | Status | Where / note |
|---|---|---|

### Open questions
<decisions the spec left open that the implementation made silently, or things you couldn't verify and why>

### App impact
<only if an endpoint the app uses changed>
```

Severity:
- **Blocker:** a spec requirement missing or wrong, price leakage, a security hole, data loss or corruption, a failing check, a broken or irreversible migration.
- **Major:** a bug in an edge case, a query that won't scale with expected data, a scraping-rule breach, a layering violation, missing tests for a spec requirement, implementation spec out of date.
- **Minor:** design-principle issues with low impact, naming, small duplication, test quality.

Only give **Ready** if there are no Blocker or Major findings. If you found nothing at all, say so plainly and list what you checked, but first go back over price leakage, upserts and the "mark as gone" logic once more: those are where bugs hide in this codebase.
