#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Initialize the mixins module.

This module provides database mixin classes that extend the base Database
class to provide database-specific functionality for different database
systems including PostgreSQL, SQLite, MySQL, and others.

Examples
--------
Import PostgreSQL mixin:
    >>> from pygarden.mixins import PostgresMixin

Import SQLite mixin:
    >>> from pygarden.mixins import SQLiteMixin

Create a custom database class:
    >>> class MyDatabase(PostgresMixin, Database):
    ...     pass
"""

from pygarden.mixins.postgres import PostgresMixin
from pygarden.mixins.sqlite import SQLiteMixin

__all__ = [
    "PostgresMixin",
    "SQLiteMixin",
]
