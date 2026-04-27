## pyGARDEN Documentation

Welcome to the pyGARDEN docs.

pyGARDEN is a small toolkit that standardizes:

- **Environment-driven configuration**
- **Rich, centralized logging**
- **Database connections and mixins**
- **Scrapers and integrations**
- **CLI utilities and schedulers**

These docs are organized by topic:

- **Core concepts**:
  - `configuration.md`: Environment variables and configuration patterns.
  - `logging.md`: Logging setup via `pygarden.logz`.
- **Database**:
  - `database/index.md`: The `Database` abstraction and connection info.
  - `database/mixins.md`: Database mixins (Postgres, MSSQL, SQLite, etc.).
  - `database/sqlalchemy.md`: SQLAlchemy engine and session integration.
- **Scrapers**:
  - `scrapers/index.md`: Scraper framework overview.
  - `scrapers/mixins.md`: HTTP/HTML/JSON/WebSocket and other scraper mixins.
- **CLI and services**:
  - `cli.md`: CLI entry points and patterns.
  - `scheduler.md`: Background scheduler with SQLAlchemy job store.
  - `mail.md`: Email sending helpers.
  - `auth.md`: Authentication helpers.
  - `s3.md`: S3 and S3-compatible object storage helpers.
  - `file_operations.md`: File helper utilities.

Use this as a starting point; individual pages go into more detail with
examples and environment variables.
