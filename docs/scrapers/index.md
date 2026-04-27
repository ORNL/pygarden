## Scrapers

The `pygarden.scrapers` package provides a flexible framework for
pulling data from web resources. It focuses on:

- **HTTP requests and responses**
- **HTML and XML scraping**
- **JSON APIs**
- **WebSocket connections**
- **Specialized integrations** (ArcGIS, Cloudflare-protected sites, etc.)

The design mirrors pyGARDEN’s overall approach:

- Small, composable **mixins** that add behavior.
- Environment-aware configuration and logging.
- Sensible defaults for common scraping tasks.

---

## Core scraper components

Key modules include:

- `pygarden.scrapers.scraper`:
  - Base classes and shared logic for scrapers.
- `pygarden.scrapers.connections`:
  - Helpers for connection/session lifecycle.
- `pygarden.scrapers.static`:
  - Utilities for scraping static content.
- `pygarden.scrapers.csvs`:
  - CSV-focused scraping helpers.
- `pygarden.scrapers.webdriver` / `seleniumscraper`:
  - Browser-based scraping via Selenium or similar tools.

These work together with the mixins in `pygarden.scrapers.mixins` to
support a wide variety of scraping scenarios.

See `scrapers/mixins.md` for details on individual mixins.

