"""
Provide authentication methods.

This module provides authentication utilities including LDAP authentication
and password hashing functionality. It supports secure password storage
using salt and various hashing algorithms.

The module provides:
- LDAP authentication with configurable server settings
- Password hashing with salt generation
- Support for multiple hashing algorithms
- Environment variable based configuration

Examples
--------
Authenticate against LDAP::

    >>> user = authenticate_ldap_user("jdoe", "securepassword")

Generate a salt and hash a password::

    >>> salt = generate_salt()
    >>> hashed = hash_password("mypassword", salt)

Use different hashing algorithms::

    >>> import hashlib
    >>> salt = generate_salt()
    >>> hashed = hash_password("mypassword", salt, hashlib.sha256)

Notes
-----
Environment Variables Required for LDAP:
    - LDAP_SERVER: URL of the LDAP server
    - LDAP_ROOT_DN: The root distinguished name (DN) for LDAP queries

Optional Environment Variables:
    - LDAP_USER_DN: Template for constructing the user's DN (default: "uid={uid},ou=Users")
    - LDAP_USER_SEARCH_FILTER: LDAP search filter to find the user (default: "(uid={uid})")

Dependencies:
    - ldap3: For LDAP authentication (install with: pip install ldap3)
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

    :param uid: The user ID of the user to authenticate
    :type uid: str
    :param password: The password of the user to authenticate
    :type password: str
    :return: The user's LDAP entry if authentication is successful, None otherwise
    :rtype: ldap3.Entry or None
    :raises ldap3.core.exceptions.LDAPException: If there is an issue connecting to the LDAP server or during the search

    Examples
    --------
    Authenticate a user::

        >>> user = authenticate_ldap_user('jdoe', 'securepassword')
        >>> if user:
        ...     print(f"Authenticated: {user.uid.value}")
        ... else:
        ...     print("Authentication failed")

    The function will use environment variables for LDAP configuration::

        >>> import os
        >>> os.environ['LDAP_SERVER'] = 'ldap://ldap.example.com'
        >>> os.environ['LDAP_ROOT_DN'] = 'dc=example,dc=com'
        >>> user = authenticate_ldap_user('jdoe', 'password')

    Notes
    -----
    Environment Variables:
        - LDAP_SERVER: URL of the LDAP server
        - LDAP_ROOT_DN: The root distinguished name (DN) for LDAP queries
        - LDAP_USER_DN: Template for constructing the user's DN (default: "uid={uid},ou=Users")
        - LDAP_USER_SEARCH_FILTER: LDAP search filter to find the user (default: "(uid={uid})")

    The function returns None if authentication fails, or the LDAP entry object
    if authentication succeeds. The LDAP entry contains all the user's attributes.
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

    This function generates a cryptographically secure random salt using
    os.urandom() and converts it to a string format suitable for password
    hashing.

    :return: A random salt string suitable for password hashing
    :rtype: str

    Examples
    --------
    >>> salt = generate_salt()
    >>> print(len(salt))  # Should be a reasonable length
    64
    >>> print(salt)  # Should be a random string
    'a1b2c3d4e5f6...'

    Generate multiple salts::

        >>> salt1 = generate_salt()
        >>> salt2 = generate_salt()
        >>> salt1 != salt2  # Should be different
        True

    Notes
    -----
    This function uses os.urandom(32) to generate 32 bytes of random data,
    which is then converted to a string representation. The salt is used
    to prevent rainbow table attacks on password hashes.
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

    This function hashes a password using the provided salt and hash algorithm.
    It supports various hashing algorithms and allows customization of parameters
    like iteration count for PBKDF2.

    :param password: The password to hash
    :type password: str
    :param salt: The salt to use for hashing
    :type salt: str
    :param hash_algorithm: The hashing algorithm to use
    :type hash_algorithm: callable
    :param *args: Additional arguments for the hashing algorithm
    :type *args: Any
    :param **kwargs: Additional keyword arguments for the hashing algorithm
    :type **kwargs: Any
    :return: The hexadecimal representation of the hashed password
    :rtype: str

    Examples
    --------
    Hash a password with default settings::

        >>> salt = generate_salt()
        >>> hashed = hash_password("mypassword", salt)
        >>> print(len(hashed))  # Should be a hex string
        128

    Hash a password with custom parameters::

        >>> salt = generate_salt()
        >>> hashed = hash_password("mypassword", salt, iterations=100000)
        >>> print(hashed[:10])  # First 10 characters of hash
        'a1b2c3d4e5'

    Using a different hash algorithm::

        >>> import hashlib
        >>> salt = generate_salt()
        >>> hashed = hash_password("mypassword", salt, hashlib.sha256)
        >>> print(hashed[:10])
        'f1e2d3c4b5'

    Using SHA-512 with custom parameters::

        >>> salt = generate_salt()
        >>> hashed = hash_password("mypassword", salt, hashlib.sha512)
        >>> print(len(hashed))  # SHA-512 produces 128 character hex string
        128

    Notes
    -----
    The default hash algorithm is hashlib.pbkdf2_hmac with SHA-256,
    which is a secure choice for password hashing. The function
    automatically encodes the password and salt as bytes before
    passing them to the hash algorithm.

    Common parameters for PBKDF2:
        - iterations: Number of iterations (default varies by algorithm)
        - dklen: Length of derived key (default varies by algorithm)
        - hash_name: Hash function to use (default: 'sha256')
    """
    return hash_algorithm(password.encode(), salt.encode(), *args, **kwargs).hex()
