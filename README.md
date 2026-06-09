# MagicBricks Property Rate Trends Scraper

Scrapes property rate trends, price history, locality ratings, and reviews from [MagicBricks.com](https://www.magicbricks.com).

## Architecture

4-stage pipeline where each stage consumes the previous stage's output:

```
Stage 1 ──> Stage 2 ──> Stage 3 ──> Stage 4
Cities      Localities   Price        Ratings &
            + Price      Trends +     Reviews
            Ranges       History
```

| Stage | What it does | Method |
|-------|-------------|--------|
| **1** | Scrapes city list from main property rates page | HTML parsing |
| **2** | For each city, scrapes sub-property types, localities, and price ranges | DWR API calls |
| **3** | For each locality, scrapes detailed price trends (sale/rent avg, QoQ, price history graph, nearby comparison) | HTML + DWR API calls |
| **4** | For each locality, scrapes ratings and reviews (category ratings, individual reviews, rating distribution) | HTML parsing |

Stages 2 and 3 reverse-engineer MagicBricks' DWR (Direct Web Remoting) API — they call the same endpoints the website's JavaScript uses, not HTML scraping.

## Setup

```bash
pip install -r requirements.txt
```

### Environment Variables (optional, for DB)

The database loaders use these env vars with defaults:

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_NAME` | `magicbricks` | Database name |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | `postgres` | Database password |
| `DB_HOST` | `localhost` | Database host |
| `DB_PORT` | `5432` | Database port |

If DB credentials aren't set, the scraper still works — it skips DB loading and saves to CSV only.

## Usage

Run all stages sequentially:

```bash
python main.py all
```

Run a specific stage:

```bash
python main.py 1   # Stage 1 only (rescrapes cities)
python main.py 2   # Stage 2 only (rescrapes localities using existing city CSV)
python main.py 3   # Stage 3 only (rescrapes price trends using existing stage 2 CSV)
python main.py 4   # Stage 4 only (rescrapes ratings using existing stage 3 CSV)
```

Each stage reads the previous stage's latest CSV from `data/stageN/`, so you can run stages independently after the initial scrape.

## Output

### CSV Files

All outputs follow the naming convention:

```
data/stageN/magic_brick_property_price_trends_{HH}_{MM}_{SS}_{dd}_{mm}_{yy}.csv
```

| Stage | Directory | Key fields |
|-------|-----------|------------|
| 1 | `data/stage1/` | `city_name`, `property_type`, `city_url` |
| 2 | `data/stage2/` | `city_name`, `sub_property_type`, `locality`, `sale_price_range`, `sale_average_price`, `sale_q_o_q`, `view_trends_link` |
| 3 | `data/stage3/` | `locality_name`, `sale_avg_price`, `sale_qoq`, `rent_avg_price`, `rent_qoq`, `price_history` (JSON), `nearby_localities` (JSON), `reviews_link`, `locality_rating`, `props_for_sale`, `props_for_rent` |
| 4 | `data/stage4/` | `locality_name`, `environment_rating`, `commuting_rating`, `places_of_interest_rating`, `overall_rating_distribution` (JSON), `total_reviews`, `reviews_data` (JSON array) |

### Database

If PostgreSQL is configured, each run creates a timestamped table (same naming convention as CSV files) in the database and inserts the records. DB loading failures are non-fatal — the scraper continues and saves CSV regardless.

## Project Structure

```
├── main.py                  # CLI orchestrator
├── scraper/
│   ├── stage1/scraper.py    # City list scraper
│   ├── stage2/scraper.py    # Locality + price range scraper (DWR)
│   ├── stage3/scraper.py    # Price trend detail scraper (DWR)
│   └── stage4/scraper.py    # Ratings & reviews scraper
├── database/
│   ├── stage1/db_config.py  # DB connection config
│   ├── stage1/db_loader.py
│   ├── stage2/db_loader.py
│   ├── stage3/db_loader.py
│   └── stage4/db_loader.py
└── data/
    ├── stage1/
    ├── stage2/
    ├── stage3/
    └── stage4/
```

## Notes

- DWR API sessions are maintained via `requests.Session` — cookies are preserved across calls.
- A 1-1.5s delay is applied between all requests to avoid rate limiting.
- If a stage fails or returns no data, downstream stages will detect it and print an error rather than crash.
- The `proxies/` directory and `data/` directory are gitignored.
