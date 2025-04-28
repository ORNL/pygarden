"""Provide authentication methods."""

import hashlib
import os
from typing import Any, Callable, Dict
from urllib.parse import urlencode, urlparse

from pygarden.env import check_environment as ce

try:
    from ldap3 import ALL, SUBTREE, Connection, Server
    from ldap3.core.exceptions import LDAPBindError, LDAPException
except ImportError:
    import sys

    from pygarden.logz import create_logger

    log = create_logger()
    log.warn("To use this module, install common-package[auth] extra.")
    sys.exit(1)


def authenticate_ldap_user(uid, password):
    """
    Authenticates a user against an LDAP server using their user ID and password.

    This function retrieves the necessary LDAP configuration from environment variables,
    establishes a connection to the LDAP server, and attempts to bind with the provided
    credentials. If the binding is successful, it searches for the user's entry and returns it.

    Parameters:
    - uid (str): The user ID of the LDAP account to authenticate.
    - password (str): The password for the LDAP account.

    Returns:
    - ldap3.Entry: The LDAP entry of the authenticated user if successful.
    - None: If the authentication fails (e.g., incorrect credentials or issues with server connection).

    Environment Variables:
    - LDAP_SERVER: URL of the LDAP server. .
    - LDAP_ROOT_DN: The root distinguished name (DN) for LDAP queries.
    - LDAP_USER_DN: Template for constructing the user's DN. Default is "uid={uid},ou=Users".
    - LDAP_USER_SEARCH_FILTER: LDAP search filter to find the user. Default is "(uid={uid})".

    Example:
    To authenticate a user with ID 'jdoe' and password 'securepassword', you can call:
    authenticate_ldap_user('jdoe', 'securepassword')

    Raises:
    - ldap3.core.exceptions.LDAPException: If there is an issue connecting to the LDAP server or during the search.
    """
    ldap_server = ce("LDAP_SERVER")
    root_dn = ce("LDAP_ROOT_DN")
    user_dn = ce("LDAP_USER_DN", f"uid={uid},ou=Users")
    user_search_filter = ce("LDAP_USER_SEARCH_FILTER", f"(uid={uid})")
    dn = f"{user_dn},{root_dn}"
    server = Server(ldap_server, get_info=ALL)
    connection = Connection(server, user=dn, password=password)
    # check if binding to the connection works
    if not connection.bind():
        return None
    connection.search(root_dn, user_search_filter, attributes=["*"])
    return connection.entries[0]


def generate_salt() -> str:
    return str(os.urandom(32)).replace("\\", "").replace("b", "")


def hash_password(
    password: str,
    salt: str,
    hash_algorithm: Callable[..., Any] = hashlib.pbkdf2_hmac,
    *args: Any,
    **kwargs: Any,
) -> str:
    return hash_algorithm(password.encode(), salt.encode(), *args, **kwargs).hex()
