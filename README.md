# X Scraper

A minimal MVP ecommerce scraper for Iranian WordPress/WooCommerce storefronts.

## Project overview

`X Scraper` is designed to extract structured product information from ecommerce pages using a layered approach:
- primary extraction from embedded JSON-LD metadata,
- secondary extraction from Open Graph and Twitter meta tags,
- fallback extraction using generic DOM selectors for common WooCommerce/Elementor layouts.

The project is intended as an MVP for general ecommerce scraping. It is not a universal crawler for every website; some stores may require custom adapters or site-specific scraping rules.

## Architecture

The project is organized into clear responsibilities:
- `application/cli.py`: command-line entrypoint and orchestrator.
- `application/extractor/`: extraction pipeline and site discovery.
  - `extract.py`: product page fetching, parsing, normalization, and error handling.
  - `robots_parser.py`: robots.txt, sitemap discovery, and product URL extraction.
  - `_resources.py`: shared helpers for text cleaning, price normalization, and timestamps.
- `application/database/`: SQLite persistence and schema management.
  - `sqlite.py`: product upsert, price-history recording, product lookup, and schema creation.
- `application/data_management/`: higher-level database helper for inserting scraped records.
- `application/driver/chrome.py`: Selenium Chrome driver configuration.
- `config.py`: environment-configurable defaults for scraper behavior.
- `logger/logger.py`: centralized logging setup.

This separation makes the scraper easier to extend, test, and maintain.

## Features

- Scrape single product URLs or discover product links from a website's `robots.txt` and sitemap.
- Use either raw HTTP requests or Selenium for JavaScript-heavy pages.
- Persist products in SQLite with normalized fields and price history tracking.
- Record each scrape as a time-series entry in `price_history`, while keeping a single canonical product row.
- Support environment-driven configuration for runtime behavior.

## Installation

1. Create and activate a Python virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

2. Install runtime dependencies:

```powershell
pip install -r requirements.txt
```

3. (Optional) Install the package in editable mode:

```powershell
pip install -e .
```

4. Install Chrome and a matching ChromeDriver for Selenium if you plan to use `--method selenium`.

## Usage

### Scrape product URLs

```powershell
python -m application.cli --product-url https://example.com/product/123 https://example.com/product/456
```

### Scan `robots.txt` and sitemaps for product pages

```powershell
python -m application.cli --site-url https://example.com
```

### Choose the fetch method

Use raw requests:

```powershell
python -m application.cli --product-url https://example.com/product/123 --method requests
```

Use Selenium with headless mode:

```powershell
python -m application.cli --product-url https://example.com/product/123 --method selenium --headless
```

### Optional CLI flags

- `--db-file`: SQLite database file path (default from config).
- `--headless`: Enable Selenium headless mode.
- `--verbose`: Enable debug logging.

### Installed CLI entrypoint

After `pip install -e .`, the package exposes the `x-scraper` CLI command:

```powershell
x-scraper --product-url https://example.com/product/123
```

## Configuration

The scraper supports environment variable overrides with the `X_SCRAPER_` prefix.

Example environment variables:

```powershell
$env:X_SCRAPER_DB_FILE = 'data.db'
$env:X_SCRAPER_METHOD = 'requests'
$env:X_SCRAPER_REQUEST_TIMEOUT = '15'
$env:X_SCRAPER_SELENIUM_HEADLESS = 'True'
```

Key configuration values in `config.py`:

- `X_SCRAPER_DB_FILE`: SQLite output file.
- `X_SCRAPER_METHOD`: `requests` or `selenium`.
- `X_SCRAPER_REQUEST_TIMEOUT`: seconds for HTTP requests.
- `X_SCRAPER_SELENIUM_HEADLESS`: `True` / `False`.
- `X_SCRAPER_SELENIUM_WINDOW_SIZE`: browser window size for Selenium.
- `X_SCRAPER_SELENIUM_IMPLICIT_WAIT`: Selenium implicit wait seconds.

## Database design

The project uses SQLite for persistence and supports both product snapshots and price history.

### `products`

Canonical product records:
- `id`: primary key
- `url`: unique product URL
- `title`
- `price`
- `description`
- `images`: JSON text array
- `name`
- `company_name`
- `category`: JSON text array
- `currency`
- `availability`
- `sku`
- `mpn`
- `rating`
- `review_count`
- `created_at`
- `updated_at`

### `price_history`

Time-series history records:
- `id`: primary key
- `product_id`: foreign key to `products.id`
- `price`
- `currency`
- `availability`
- `scraped_at`

This design preserves a single canonical product entry while storing every scrape's price snapshot separately.

## Logging

The scraper writes logs to `scraper.log` by default. Enable detailed output with `--verbose`.

## Testing

Run the unit tests with either unittest or pytest:

```powershell
python -m unittest discover -s tests -p '*.py' -v
```

Or, if `pytest` is installed:

```powershell
pytest -q
```

Development dependencies are listed in `requirements-dev.txt`.

## Packaging

This project is configured via `pyproject.toml`.

- `name`: `x-scraper`
- `version`: `0.1.0`
- `dependencies`: runtime Python packages.
- `project.scripts.x-scraper`: CLI entrypoint.
- `project.optional-dependencies.dev`: dev/test dependencies.

## Notes for Iranian ecommerce scraping

Many Iranian ecommerce storefronts are built on WordPress/WooCommerce and may use Elementor or other page builders. This scraper focuses on extracting structured metadata from such pages, but site-specific layouts or custom markup may still require custom adapter code.

When a site fails to scrape correctly:
- inspect the page source,
- add custom selectors or parsing rules in `application/extractor/extract.py`,
- keep the generic pipeline for most standard product pages.

## Repository hygiene

The repository ignores local artifacts such as:
- `.venv`
- `*.db`
- build artifacts
- test caches

Do not commit generated database files or local virtual environments.

## License

MIT License
