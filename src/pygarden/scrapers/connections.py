#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provide connection utilities for scrapers.

This module provides utility functions for managing web scraping connections,
including connection pooling, retry logic, and session management.

Examples
--------
Create a session with retry logic:
    >>> session = create_session(max_retries=3)

Make a request with connection pooling:
    >>> response = make_request("https://example.com", session=session)
"""
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pygarden.env import check_environment as ce


def create_uri(logger=logging.getLogger(ce("ETL_LOGGER", "main"))):
    """Create a URI for a connection to the Postgresql database."""
    user = ce("DB_USER", "guest")
    pwd = ce("DB_PASS", "abc123")
    host = ce("DB_HOST", "db")
    db = ce("DB_DB", "covidb")
    port = ce("DB_PORT", "5432")
    uri = f"postgres://{user}:{pwd}@{host}:{port}/{db}"
    logger.info(f"Created URI: {uri}")
    return uri


def create_session(max_retries: int = 3, backoff_factor: float = 0.3) -> requests.Session:
    """
    Create a requests session with retry logic.

    This function creates a requests Session object with automatic retry
    logic for failed requests. It uses exponential backoff to avoid
    overwhelming the server.

    Parameters
    ----------
    max_retries : int, optional
        Maximum number of retries for failed requests, by default 3
    backoff_factor : float, optional
        Backoff factor for retry delays, by default 0.3

    Returns
    -------
    requests.Session
        A configured requests session with retry logic

    Examples
    --------
    Create a basic session:
        >>> session = create_session()
        >>> response = session.get("https://example.com")

    Create a session with custom retry settings:
        >>> session = create_session(max_retries=5, backoff_factor=0.5)
        >>> response = session.get("https://api.example.com")
    """
    session = requests.Session()
    
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


def make_request(url: str, session: requests.Session = None, **kwargs) -> requests.Response:
    """
    Make an HTTP request with optional session management.

    This function makes an HTTP GET request to the specified URL,
    optionally using a provided session for connection pooling and
    retry logic.

    Parameters
    ----------
    url : str
        The URL to request
    session : requests.Session or None, optional
        Session to use for the request. If None, creates a new session, by default None
    **kwargs
        Additional keyword arguments for requests.get()

    Returns
    -------
    requests.Response
        The response object

    Examples
    --------
    Make a simple request:
        >>> response = make_request("https://example.com")
        >>> print(response.status_code)
        200

    Make a request with a session:
        >>> session = create_session()
        >>> response = make_request("https://api.example.com", session=session)
        >>> print(response.json())
        {'key': 'value'}

    Make a request with custom headers:
        >>> response = make_request(
        ...     "https://api.example.com",
        ...     headers={'Authorization': 'Bearer token'}
        ... )
    """
    if session is None:
        session = create_session()
    
    return session.get(url, **kwargs)
