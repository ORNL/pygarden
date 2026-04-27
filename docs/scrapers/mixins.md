## Scraper Mixins

The `pygarden.scrapers.mixins` package contains mixins that extend core
scraper classes with specialized capabilities. They are designed to be
composed, so you can build scrapers that only depend on the features
you need.

This page summarizes the main mixins and what they are used for.

---

## HTML and HTML Soup Mixins

Modules:

- `pygarden.scrapers.mixins.html`
- `pygarden.scrapers.mixins.html_soup`

Responsibilities:

- Fetch and parse HTML content.
- Provide helpers for:
  - Selecting elements.
  - Extracting text and attributes.
  - Handling character encodings.

Use `html_soup` when you want BeautifulSoup-style parsing and
manipulation of HTML documents.

---

## JSON Mixins

Module:

- `pygarden.scrapers.mixins.json`

Responsibilities:

- Interact with JSON-based HTTP APIs.
- Parse responses into Python structures.
- Provide convenience methods for:
  - GET/POST/PUT/DELETE with JSON payloads.
  - Handling common error patterns.

Use this mixin when your target endpoints mostly speak JSON.

---

## XML and XML Soup Mixins

Modules:

- `pygarden.scrapers.mixins.xml`
- `pygarden.scrapers.mixins.xml_soup`

Responsibilities:

- Parse XML responses from HTTP endpoints or files.
- Provide utilities for:
  - Traversing XML trees.
  - Extracting attributes and text content.

Use these mixins when you’re dealing with XML APIs or feeds.

---

## WebSocket Mixins

Module:

- `pygarden.scrapers.mixins.websocket`

Responsibilities:

- Manage WebSocket connections.
- Send and receive messages.
- Integrate with pyGARDEN logging and error handling.

Use this mixin for streaming data sources and real-time APIs.

---

## Cloudscraper & CFScrape Mixins

Modules:

- `pygarden.scrapers.mixins.cloudscraper`
- `pygarden.scrapers.mixins.cfscrape`

Responsibilities:

- Work with sites protected by Cloudflare or similar mechanisms.
- Wrap underlying libraries like `cloudscraper` or `cfscrape`.

Install via:

- `pip install "pygarden[scrapers]"` (or install the specific libraries
  alongside pyGARDEN).

---

## ArcGIS Mixins

Module:

- `pygarden.scrapers.mixins.arcgis`

Responsibilities:

- Interact with ArcGIS-powered endpoints.
- Simplify querying and reading geospatial data available via ArcGIS
  web services.

Use this when your target data source is ArcGIS-based and you want
pyGARDEN’s configuration and logging standards.

---

## Request Mixins

Module:

- `pygarden.scrapers.mixins.request`

Responsibilities:

- Wrap common HTTP request patterns.
- Provide:
  - Session management.
  - Retry strategies.
  - Error logging and handling.

This is often a building block for more specialized mixins.

---

## Putting it together

You typically define a scraper by combining a core scraper base with one
or more mixins:

```python
from pygarden.scrapers.scraper import BaseScraper
from pygarden.scrapers.mixins.html_soup import HTMLSoupMixin
from pygarden.scrapers.mixins.json import JSONMixin


class MyScraper(BaseScraper, HTMLSoupMixin, JSONMixin):
    ...
```

This lets you:

- Reuse connection/session logic.
- Add only the parsing and transport layers you need.
- Keep configuration and logging consistent across scrapers.

