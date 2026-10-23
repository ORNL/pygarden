# Changelog

All notable changes to this project will be documented in this file.

## [0.3.36] - 2026-08-21

### Removed

- Removed support for EOL Python 3.10

### Added

- Added `trellis` extra - a database framework similar mybatis but for Python.
- Add a reusable FastAPI authentication plugin for DOE OneID, including
  PostgreSQL-backed registration, approval, and session management.
- Add the `oneid` optional dependency group and include it in the `all` extra.
- Added and expanded the `duckdb` extra to be more in-line with the other extras.

### Changed

- Commit successful database context-manager transactions when
  `commit_on_exit` is enabled, roll back unsuccessful transactions, and stop
  committing implicitly from `Database.close()`.
- Expand the database mixin documentation with Async PostgreSQL, MSSQL, and
  pandas examples.

[0.3.36]: https://github.com/ornl/pygarden/releases/tag/v0.3.36
