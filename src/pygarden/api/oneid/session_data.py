#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Session data model for the OneID auth plugin."""

from pydantic import BaseModel


class SessionData(BaseModel):
    """
    Stores the authenticated user's identity in the session cookie.

    :param user_id: Internal user ID from the users table.
    :param email: User's email address (login identifier).
    :param first_name: Given name from the identity provider.
    :param last_name: Family name from the identity provider.
    :param admin: Whether the user has admin privileges.
    :param us_citizen: DOE citizenship flag (optional; default ``False``).
    :param affiliation: DOE affiliation string (optional; default ``""``).
    """

    user_id: int
    email: str
    first_name: str
    last_name: str
    admin: bool
    us_citizen: bool = False
    affiliation: str = ""
