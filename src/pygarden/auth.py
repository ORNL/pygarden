"""
Provide authentication methods.

This module provides authentication utilities including LDAP authentication
and password hashing functionality. It supports secure password handling
with salt generation and various hashing algorithms.

**Dependencies:**
    ldap3: Required for LDAP authentication (install with common-package[auth])

**Usage Example:**
    >>> salt = generate_salt()
    >>> hashed = hash_password('mypassword', salt)
    >>> user = authenticate_ldap_user('jdoe', 'password')
"""

import hashlib
import importlib.util
import os
import sys
from typing import Any, Callable

from pygarden.env import check_environment as ce
from pygarden.logz import create_logger

log = create_logger()

if importlib.util.find_spec("ldap3") is not None:
    from ldap3 import ALL, Connection, Server
else:
    log.warn("To use this module, install common-package[auth] extra.")
    sys.exit(1)


def authenticate_ldap_user(uid: str, password: str) -> Any:
    """
    Authenticate a user against an LDAP server using their user ID and password.

    This function retrieves the necessary LDAP configuration from environment variables,
    establishes a connection to the LDAP server, and attempts to bind with the provided
    credentials. If the binding is successful, it searches for the user's entry and returns it.

    **Environment Variables:**

    * LDAP_SERVER: URL of the LDAP server.
    * LDAP_ROOT_DN: The root distinguished name (DN) for LDAP queries.
    * LDAP_USER_DN: Template for constructing the user's DN. Default is "uid={uid},ou=Users".
    * LDAP_USER_SEARCH_FILTER: LDAP search filter to find the user. Default is "(uid={uid})".

    **Example:**

    To authenticate a user with ID 'jdoe' and password 'securepassword', you can call:

    .. code-block:: python

        authenticate_ldap_user('jdoe', 'securepassword')

    :param uid: The user ID of the user to authenticate.
    :type uid: str
    :param password: The password of the user to authenticate.
    :type password: str
    :return: The user's LDAP entry if authentication is successful, None otherwise.
    :rtype: ldap3.Entry or None
    :raises ldap3.core.exceptions.LDAPException: If there is an issue connecting
        to the LDAP server or during the search.
    :note:
        Requires the ldap3 package to be installed.
        Environment variables must be properly configured.
        Returns None if authentication fails (invalid credentials).
        The function exits the program if ldap3 is not available.
    :example:
        >>> user = authenticate_ldap_user('jdoe', 'password123')
        >>> if user:
        ...     print(f"Authenticated: {user.entry_dn}")
        ... else:
        ...     print("Authentication failed")
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
    """
    Generate a random salt for password hashing.

    :return: A random salt string for use in password hashing.
    :rtype: str
    :note:
        Uses os.urandom(32) to generate cryptographically secure random bytes.
        Removes 'b' prefix and backslashes from the string representation.
        The salt is 32 bytes (256 bits) long.
    :example:
        >>> salt = generate_salt()
        >>> len(salt)
        32
        >>> isinstance(salt, str)
        True
    """
    return str(os.urandom(32)).replace("\\", "").replace("b", "")


def hash_password(
    password: str,
    salt: str,
    hash_algorithm: Callable[..., Any] = hashlib.pbkdf2_hmac,
    *args: Any,
    **kwargs: Any,
) -> str:
    """
    Hash a password using the specified hash algorithm and salt.

    :param password: The password to hash.
    :type password: str
    :param salt: The salt to use for hashing.
    :type salt: str
    :param hash_algorithm: The hashing algorithm to use (default: PBKDF2-HMAC-SHA256).
    :type hash_algorithm: Callable, optional
    :param args: Additional arguments for the hashing algorithm.
    :param kwargs: Additional keyword arguments for the hashing algorithm.
    :return: The hashed password as a hexadecimal string.
    :rtype: str
    :note:
        Default algorithm is PBKDF2-HMAC-SHA256 (hashlib.pbkdf2_hmac).
        Password and salt are encoded as UTF-8 bytes before hashing.
        The result is returned as a hexadecimal string.
        Additional args/kwargs are passed directly to the hash algorithm.
    :example:
        >>> salt = generate_salt()
        >>> hashed = hash_password('mypassword', salt)
        >>> len(hashed)
        64  # SHA256 produces 32 bytes = 64 hex characters
        >>> hashed = hash_password('mypassword', salt, hashlib.sha256)
        >>> len(hashed)
        64
    """
    return hash_algorithm(password.encode(), salt.encode(), *args, **kwargs).hex()
