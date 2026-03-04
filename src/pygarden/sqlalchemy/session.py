#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session utilities for SQLAlchemy integration.

These helpers are intentionally lightweight and can be used either
directly or via `SQLAlchemyMixin`.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

from .mixins import _require_sqlalchemy


def session_factory(engine, **kwargs: Any):
    """
    Create a `sessionmaker` bound to the given Engine.

    Defaults are conservative and suitable for service-style usage.
    """
    _require_sqlalchemy()
    from sqlalchemy.orm import sessionmaker

    params = {"bind": engine, "expire_on_commit": False}
    params.update(kwargs)
    return sessionmaker(**params)


@contextmanager
def session_scope(engine, **session_kwargs: Any) -> Generator[Any, None, None]:
    """
    Provide a transactional scope around a series of operations.

    Example:

    ```python
    from sqlalchemy import text

    with session_scope(engine) as session:
        session.execute(text("SELECT 1"))
    ```

    Behavior:
    - Commit on normal exit.
    - Rollback on exception, then re-raise.
    - Always close the session.
    """
    Session = session_factory(engine, **session_kwargs)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

