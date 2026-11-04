# Spec: danbolig source (Bagsværd pilot)

Status: **agreed** (2026-11-04). Use of danbolig.dk as a source is agreed for internal testing only, within the scope below (see the scraping rules in `CLAUDE.md`).

## Goal
The first real scraping source: up to 100 current listings for sale in Bagsværd from danbolig.dk, so the game can be played with real listings. It's a pilot with a small, fixed scope (one search, at most 100 listings, a slow rate limit) to learn how the source behaves before widening it.

## What was checked (2026-11-04)
- **robots.txt** (`https://danbolig.dk/robots.txt`) only disallows `/umbraco`, `/ejendomsmaegler/butik/` and `/test`. The search page, the listing pages and `/api/v1/` are not disallowed.
- **Terms of use:** there's no terms page linked from the site. The privacy policy (`/cookie-og-privatlivspolitik/`) says that using the site means accepting "de gældende vilkår for brugen af vores indhold og tjenester", but doesn't link to them. See open question 1.
- **Search page:** `https://danbolig.dk/soeg/?q=bagsv%C3%A6rd&o=relevant&la=55.7582539&lo=12.4470019&z=13.47` gets its results from `POST https://danbolig.dk/api/v1/properties/list` (JSON). The request, read from the site's JavaScript and tried directly:
  - Body: `{"filters": [{"key": "SearchString", "value": "bagsværd"}], "orderBy": "relevant", "page": 1}`. The site also sends a `Viewport` polygon filter and `lat`/`lon` from the map, but they aren't needed: the text search alone returns the same 111 listings, so the result set doesn't depend on a viewport.
  - Paging: `page` starts at 1, with 30 listings per page plus 1–2 promo entries. On this date pages 1–4 held 30, 30, 30 and 21 listings and page 5 was empty.
  - Response: `{"totalCount": 111, "data": [{"responseType": "property" | "promo", "data": {…}}]}`. The listing fields (`propertyId`, `brokerId`, `url`, `type`, `price`, `isSold`, `isUnderSale`, `isReserved`, `soldDate`, …) are inside the entry's `data`.
  - `propertyId` and `brokerId` are strings. `propertyId` isn't always numeric and varies in length (8–20 characters, for example `1840001050`, `01210000640260121nyb`, `16-X00024523533lok`); there were 10 different `brokerId`s.
  - The 111 included 11 sold listings (`isSold`, with a `soldDate`) and 1 with `isUnderSale`. Types: Villa 59, Lejlighed 35, Rækkehus 14, Villalejlighed 3; no rentals or plots; all in 2880 Bagsværd.
  - A plain request with the scraper's `User-Agent` and no cookies gets the same response.
- **Listing page** (for example `/bolig/gladsaxe/2880/lejlighed/1840001050-184/`) is server-rendered HTML. It contains:
  - JSON-LD blocks: `Residence` with `geo.latitude` and `geo.longitude` (strings); `RealEstateListing` with `datePosted`; `ImageGallery` whose `associatedMedia[].contentUrl` are the photos in order. `@type` is a list (`["ImageGallery"]`), not a string;
  - the floor plans, in the `:floorplan2d` attribute of the `<o-property-floorplan>` element: an HTML-entity-encoded JSON list of `{description, url, …}`, where `description` names the floor (for example "1. sal"). They aren't in the JSON-LD gallery;
  - a **Boligfakta** table: Type, Udbudsform, Energimærke, Byggeår, Etage, Rum, Bad, Toilet, Plan, Boligareal, Grundareal, and under Økonomi: Kontantpris, Ejerudgift, Udbetaling, Brutto and Netto;
  - the description text, the agent's name, email and phone number, and page-view counts. None of this is used.
- **Facts vary between listings:** some have "Ombygget" (renovation year) and "Erhverv" (commercial area in the building); some have no "Plan". Every Boligfakta value the mapping uses must be optional (see "Required fields" below).
- **Images** are served from `danbolig.mindworking.eu`. The base64 path segment after `mediaDataMediaPurposeId/` decodes to `{"MediaDataId": …, "MediaPurposeId": …}`, but `MediaPurposeId` doesn't tell photos from floor plans: on `1840001050-184` the photos and the floor plan are both `22`, and `25` is the house video. That listing had 24 photos in the JSON-LD gallery and 1 floor plan in `:floorplan2d`; the page as a whole has more media URLs than that (video, sharing images), so the images must be taken from those two places only.
- **`GET /api/v1/properties/galleryMedia?propertyId=…&brokerId=…`** returns the same photos plus the video as typed JSON (`type` "Billede" or "Video"), but no floor plans. It isn't used: the listing page is needed anyway for the facts and floor plans.

## What to build

### 1. Source module `scraper/sources/danbolig.py`
A source named `danbolig` that implements the `Source` interface:

1. **Search:** POST the body above to `/api/v1/properties/list` with `page` 1, 2, 3, … and stop when a page has no entries or `totalCount` listings have been collected. Keep only entries with `responseType == "property"`; the others are promo blocks. No `Viewport`, `lat` or `lon`.
2. **Pick at most 100:** drop listings with `isSold` (they stay in the search for a while after the sale, but the game never shows them) and listings whose search `type` the game doesn't use (see the type mapping), so no places or detail requests go to listings that would be skipped. Sort the rest by (`propertyId`, `brokerId`), compared as strings, and take the first 100 (see "Why a stable order" below).
3. **Details:** fetch each picked listing's page (`https://danbolig.dk` + `url`) and parse the JSON-LD, the floor plans and the Boligfakta table.
4. **Map** each listing to a `NormalisedListing` using the mapping below. A listing that fails the required fields below, or whose page can't be fetched or parsed, counts as `failed` and is logged by `source_listing_id`; the rest of the listings are still returned.

**Required fields:** a listing fails if any of these is missing or can't be parsed: `source_listing_id`, `source_url`, `type`, `location`, `price`, at least one photo in `images`, or at least one floor plan in `floor_plans`. Every other field is `null` when it's missing or its value can't be parsed (for example an Etage like `1. sal`, `st. tv.` or `2.-3.`, or an area like `65,5 m²`), with a warning that names the listing, the field and the raw value.

The search query, the limit of 100 and the base URL are constants in the module. Nothing is configurable beyond turning the source on.

**Why a stable order:** the runner marks a listing `removed` once it hasn't been seen for 2 days. If the 100 were taken in "relevant" order, the selection would shift between runs. Listings still for sale would fall outside the 100 and be wrongly removed. Sorted by id, the same listings stay in the selection until they're sold or leave the site, and new listings are only taken in when there's room. A listing that's sold drops out of the selection and is marked `removed` by the runner after 2 days, not `sold`; that's fine, because the game only uses active listings.

### 2. Rate limit and HTTP
- All requests go through the shared `RateLimitedClient` with `requests_per_second=0.5` (one request per 2 seconds), the shared `User-Agent`, and its retries with backoff.
- `RateLimitedClient` only has `get` today, and the search is a POST. Add a `post` to the shared client (`scraper/http.py`) that goes through the same rate limit and the same retries and backoff as `get`, sharing that code rather than copying it. Retrying the search POST is safe, because it doesn't change anything on the site. Test it like `get` in `tests/scraper/test_http.py`: rate limit with the fake clock, retry on the retryable status codes and transport errors, and the `User-Agent`.
- Only the scraper's own requests count: the API pages and 100 listing pages. Images aren't downloaded; their URLs are stored.
- Expected run: 4–5 search requests (30 listings per page) and 100 page requests, so about 3.5 minutes.

### 3. Settings
- `DANBOLIG_SOURCE_ENABLED`, off by default, read in `app/config.py` and used in `enabled_sources()` like the sample source.

### 4. Parsing
- JSON-LD: find the `<script type="application/ld+json">` blocks and parse them with `json`. Pick blocks by `@type` (`Residence`, `RealEstateListing`, `ImageGallery`), not by position, and accept `@type` as either a string or a list.
- Floor plans: read the `:floorplan2d` attribute of `<o-property-floorplan>` (`html.parser` decodes the entities) and parse it with `json`. A page without the element has no floor plans, so the listing fails.
- Boligfakta: read the label/value pairs of the facts table. Match on the Danish label, and parse values such as `65 m²`, `1.`, `st.` and `3.750.000 kr.`.
- HTML parsing uses the standard library (`html.parser`); no new dependency (Answer 5).

## Field mapping

| Our field | danbolig source | Conversion / notes |
|---|---|---|
| `source` | — | `"danbolig"` |
| `source_listing_id` | search: `propertyId` + `brokerId` | `"{propertyId}-{brokerId}"`, as in the listing URL (`1840001050-184`). Unique and stable |
| `source_url` | search: `url` | `https://danbolig.dk` + `url` |
| `type` | search: `type` (same as Boligfakta "Type") | See the type table below. Unknown types are dropped in step 2 |
| `location` | JSON-LD `Residence.geo` | `latitude` and `longitude` are strings → `float`. The runner rejects points outside Denmark |
| `images` | JSON-LD `ImageGallery.associatedMedia[].contentUrl` | Required: every photo, in page order (one listing checked had 24); a listing without photos fails. Not the search API's `images`, which only has the first 3, and not other media URLs on the page. Drop the `width` parameter and keep the rest of the URL as it is |
| `floor_plans` | `<o-property-floorplan>` `:floorplan2d[].url` | In page order. Required: a listing without floor plans fails |
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
| `status` | search: `isUnderSale`, `isReserved` | `isUnderSale` → `contract_signed`; otherwise `active`, including `isReserved` (Answer 2). Sold listings were dropped in step 2, so `sold` never occurs |

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
- With `DANBOLIG_SOURCE_ENABLED=true`, `uv run python -m scraper` stores at most 100 danbolig listings from the Bagsværd search, none of them sold, and logs new, updated, deactivated and failed counts.
- Every listing stores the URLs of **all** its photos, in the order the listing page shows them, not only the 3 the search API returns. A parsing test checks that the stored photos are exactly the JSON-LD gallery's URLs on the fixture page, in order, and that the floor plans from `:floorplan2d` are in `floor_plans`, not in `images`.
- Running it again creates no duplicates, and the same listings stay selected as long as they're on the site and not sold.
- The scraper never makes more than one request per 2 seconds, GET or POST (tested with the fake clock, as in `tests/scraper/test_http.py`).
- Parsing tests run against saved fixtures in `tests/scraper/sources/fixtures/danbolig/`: search response pages (including the empty last page), and listing pages for an apartment on `st.`, an apartment on an upper floor, a house, a listing with missing facts, and listings without photos and without floor plans (which must fail). The tests never call the live site.
- The fixtures contain no personal data or listing text: saved listing pages are cut down to the JSON-LD blocks, the `<o-property-floorplan>` element and the Boligfakta table, and the agent block, description and any other markup are removed before they're committed. Saved search responses have `address`, `spotText` and other fields the source doesn't read removed.
- Parsing tests cover the required fields: a listing missing any of them is counted as `failed`, and a value that can't be parsed in any other field becomes `null`.
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
7. **One run:** the source is run once to build a test dataset and isn't re-run, so a still-for-sale listing being pushed out of the 100 and marked `removed` on a later run isn't a concern.
8. **Image size:** drop the `width` parameter, even if that means the full-size image.
9. **Hosting:** the backend only runs locally for now, and the danbolig data will be deleted later, so nothing in the code or the implementation spec has to stop the source being enabled on a hosted backend. The app loading images straight from danbolig's image server is fine at this scale.
