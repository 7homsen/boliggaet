# Spec: danbolig source (Bagsværd pilot)

Status: **agreed** (2026-11-04). Use of danbolig.dk as a source is agreed for internal testing only, within the scope below (see the scraping rules in `CLAUDE.md`).

## Goal
The first real scraping source: up to 100 current listings for sale in Bagsværd from danbolig.dk, so the game can be played with real listings. It's a pilot with a small, fixed scope (one search, at most 100 listings, a slow rate limit) to learn how the source behaves before widening it.

## What was checked (2026-11-04)
- **robots.txt** (`https://danbolig.dk/robots.txt`) only disallows `/umbraco`, `/ejendomsmaegler/butik/` and `/test`. The search page, the listing pages and `/api/v1/` are not disallowed.
- **Terms of use:** there's no terms page linked from the site. The privacy policy (`/cookie-og-privatlivspolitik/`) says that using the site means accepting "de gældende vilkår for brugen af vores indhold og tjenester", but doesn't link to them. See open question 1.
- **Search page:** `https://danbolig.dk/soeg/?q=bagsv%C3%A6rd&o=relevant&la=55.7582539&lo=12.4470019&z=13.47` gets its results from `POST https://danbolig.dk/api/v1/properties/list` (JSON). On this date it reported `totalCount: 111`. The request body wasn't inspected; it needs to be read from the browser's developer tools before implementation.
- **Listing page** (for example `/bolig/gladsaxe/2880/lejlighed/1840001050-184/`) is server-rendered HTML. It contains:
  - JSON-LD blocks: `Residence` with `geo.latitude` and `geo.longitude`; `RealEstateListing` with `datePosted`; `ImageGallery` with every image URL in order;
  - a **Boligfakta** table: Type, Udbudsform, Energimærke, Byggeår, Etage, Rum, Bad, Toilet, Plan, Boligareal, Grundareal, and under Økonomi: Kontantpris, Ejerudgift, Udbetaling, Brutto and Netto;
  - the description text, the agent's name, email and phone number, and page-view counts. None of this is used.
- **Facts vary between listings:** some have "Ombygget" (renovation year) and "Erhverv" (commercial area in the building); some have no "Plan". Every fact the mapping uses must be optional.
- **Images** are served from `danbolig.mindworking.eu`. The base64 path segment after `mediaDataMediaPurposeId/` decodes to JSON with a `MediaPurposeId`: `22` is a photo and `25` is a floor plan (one listing checked: 34 photos, 1 floor plan).

## What to build

### 1. Source module `scraper/sources/danbolig.py`
A source named `danbolig` that implements the `Source` interface:

1. **Search:** page through `POST /api/v1/properties/list` with the Bagsværd search above until every result has been fetched. Keep only entries with `responseType == "property"`; the others are promo blocks.
2. **Pick at most 100:** sort the results by `propertyId` and take the first 100 (see "Why a stable order" below).
3. **Details:** fetch each picked listing's page (`https://danbolig.dk` + `url`) and parse the JSON-LD and the Boligfakta table.
4. **Map** each listing to a `NormalisedListing` using the mapping below. A listing that can't be parsed counts as `failed`; types the game doesn't use are skipped.

The search query, the limit of 100 and the base URL are constants in the module. Nothing is configurable beyond turning the source on.

**Why a stable order:** the runner marks a listing `removed` once it hasn't been seen for 2 days. If the 100 were taken in "relevant" order, the selection would shift between runs. Listings still for sale would fall outside the 100 and be wrongly removed. Sorted by `propertyId`, the same listings stay in the selection until they actually leave the site, and new listings are only taken in when there's room.

### 2. Rate limit and HTTP
- All requests go through the shared `RateLimitedClient` with `requests_per_second=0.5` (one request per 2 seconds), the shared `User-Agent`, and its retries with backoff.
- Only the scraper's own requests count: the API pages and 100 listing pages. Images aren't downloaded; their URLs are stored.
- Expected run: about 5 search requests and 100 page requests, so about 3.5 minutes.

### 3. Settings
- `DANBOLIG_SOURCE_ENABLED`, off by default, read in `app/config.py` and used in `enabled_sources()` like the sample source.

### 4. Parsing
- JSON-LD: find the `<script type="application/ld+json">` blocks and parse them with `json`. Pick blocks by `@type` (`Residence`, `RealEstateListing`, `ImageGallery`), not by position.
- Boligfakta: read the label/value pairs of the facts table. Match on the Danish label, and parse values such as `65 m²`, `1.`, `st.` and `3.750.000 kr.`.
- HTML parsing uses the standard library (`html.parser`); no new dependency (Answer 5).

## Field mapping

| Our field | danbolig source | Conversion / notes |
|---|---|---|
| `source` | — | `"danbolig"` |
| `source_listing_id` | search: `propertyId` + `brokerId` | `"{propertyId}-{brokerId}"`, as in the listing URL (`1840001050-184`). Unique and stable |
| `source_url` | search: `url` | `https://danbolig.dk` + `url` |
| `type` | search: `type` (same as Boligfakta "Type") | See the type table below. Unknown types are skipped |
| `location` | JSON-LD `Residence.geo` | `latitude` and `longitude` are strings → `float`. The runner rejects points outside Denmark |
| `images` | JSON-LD `ImageGallery.associatedMedia[].contentUrl` with `MediaPurposeId` 22 | In page order. Drop the `width` parameter and keep the rest of the URL as it is |
| `floor_plans` | the same gallery, or the page's image URLs, with `MediaPurposeId` 25 | In page order; empty list if there are none |
| `energy_rating` | Boligfakta "Energimærke" | `A2020`, `A2015`, `A2010`, `B`…`G` as they are. Anything else (for example old labels like `A1`, or "Ikke oplyst") → `null` |
| `build_year` | Boligfakta "Byggeår" | int; `null` if missing |
| `renovation_year` | Boligfakta "Ombygget" | int; `null` if missing (most listings don't have it) |
| `floors` | Boligfakta "Plan" | int: the building's floors (Answer 4); `null` if missing |
| `floor` | Boligfakta "Etage" | `st.` → 0, `1.` → 1, `kld.` → -1; only for apartments, `null` for houses |
| `rooms` | Boligfakta "Rum" | int |
| `bathrooms` | Boligfakta "Bad" | int |
| `toilets` | Boligfakta "Toilet" | int |
| `square_meters` | Boligfakta "Boligareal" | `"65 m²"` → 65 (thousands separator `.`) |
| `listed_date` | — | Always `null`. `datePosted` may be a "last published" date rather than the market date (Answer 3) |
| `price` | search: `price` | `3750000.0` → int `3750000`. Cross-check with Boligfakta "Kontantpris" in a test |
| `status` | search: `isSold`, `isUnderSale`, `isReserved` | `isSold` → `sold`; `isUnderSale` → `contract_signed`; otherwise `active`, including `isReserved` (Answer 2) |

### Type mapping

| danbolig `type` | Mapped to | Game type |
|---|---|---|
| Lejlighed | ejerlejlighed | apartment |
| Villalejlighed | ejerlejlighed | apartment |
| Andelsbolig | andelsbolig | apartment |
| Villa | villa | house |
| Rækkehus | rækkehus | house |
| Landejendom | landejendom | house |
| Fritidshus | fritidshus | house |
| Anything else (Helårsgrund, Fritidsgrund, Projekt, Erhverv, …) | — | skipped |

The source module translates danbolig's names to the shared names and then uses `map_property_type()`, so the shared mapping stays the single list of what the game accepts.

### Deliberately not stored or logged
- Address, postcode and city; the description text; `spotText` (marketing text that can mention the price or its level).
- Ejerudgift, Udbetaling, Brutto, Netto, Grundareal, `hasNewPrice` and page views: they give the price away or aren't in the data model.
- The agent's name, email and phone number, and the broker shop. Log lines name listings only by `source_listing_id`.

## Out of scope
- Other areas than Bagsværd, more than 100 listings, other agent chains or sites.
- Scheduling: the scraper is still run manually.
- Downloading or hosting images.
- Detecting price changes or price history.

## Acceptance
- With `DANBOLIG_SOURCE_ENABLED=true`, `uv run python -m scraper` stores at most 100 danbolig listings from the Bagsværd search, with at least one image each, and logs new, updated, deactivated and failed counts.
- Running it again creates no duplicates, and the same listings stay selected as long as they're on the site.
- The scraper never makes more than one request per 2 seconds (tested with the fake clock, as in `tests/scraper/test_http.py`).
- Parsing tests run against saved fixtures in `tests/scraper/sources/fixtures/danbolig/`: one search response, and listing pages for an apartment on `st.`, an apartment on an upper floor, a house, and a listing with missing facts. The tests never call the live site.
- A test checks that no agent contact details, address or description end up in a `NormalisedListing`.
- `GET /game` can return danbolig listings, and its response shape is unchanged.
- `ruff check`, `mypy` and `pytest` pass, and `docs/implementation-spec.md` lists the new source.

## Open questions
None.

## Answers
1. **Permission:** we won't ask danbolig. The data is a small sample used only for internal testing while the game is developed, not for anything else. So the danbolig data stays in local and test databases and isn't served by a hosted backend.
2. **`isReserved`:** a reserved listing is treated as `active`, so it can appear in the game.
3. **`datePosted`:** it isn't certain that it's the date the listing went on the market (it may be when the page was last published, which could also hint at a price change), so `listed_date` is `null` for danbolig listings.
4. **"Plan":** it's the building's floors, which matches our `floors` field. Checked on four apartments: 1st floor with Plan 2 (the description says a two-storey building), 3rd floor with Plan 3, 9th floor in a high-rise with Plan 15, and a ground-floor villa apartment with no Plan at all (so `null`). Plan was never lower than the apartment's floor.
5. **HTML parsing:** the standard library's `html.parser`; no new dependency.
6. **Internal API:** using `/api/v1/properties/list` is fine. If its shape changes, the parser fails clearly and the runner's partial-run check stops removals.
