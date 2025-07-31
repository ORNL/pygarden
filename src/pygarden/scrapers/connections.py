#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provide connection methods such as Postgres or sqlalchemy engine."""

import logging

from pygarden.env import check_environment as ce


def create_uri(logger=logging.getLogger(ce("ETL_LOGGER", "main"))):
    """Create a URI for a connection to the Postgresql database.

    :param logger: Logger instance to use.
    :returns: PostgreSQL connection URI.
    :rtype: str
    """
    user = ce("DB_USER", "guest")
    pwd = ce("DB_PASS", "abc123")
    host = ce("DB_HOST", "db")
    db = ce("DB_DB", "covidb")
    port = ce("DB_PORT", "5432")
    uri = f"postgres://{user}:{pwd}@{host}:{port}/{db}"
    logger.info(f"Created URI: {uri}")
    return uri
