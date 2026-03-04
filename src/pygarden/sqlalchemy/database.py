#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Concrete Database implementation that exposes SQLAlchemy engines and sessions.
"""

from __future__ import annotations

from pygarden.database import Database
from .mixins import SQLAlchemyMixin


class SQLAlchemyDatabase(Database, SQLAlchemyMixin):
    """Database implementation supporting SQLAlchemy engines and sessions."""

    # No additional behavior is required here; all database configuration
    # is provided by `Database` and the SQLAlchemy integration by
    # `SQLAlchemyMixin`.

