"""OIDC authorization-code flow and validated identity helpers for OneID."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import ipaddress
import json
import secrets
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import jwt
import requests
from authlib.integrations.requests_client import OAuth2Session
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, Request, Response

from . import config

TRANSACTION_COOKIE = "oneid_oidc_transaction"
TRANSACTION_MAX_AGE_SECONDS = 600
APPROVED_ID_TOKEN_ALGORITHMS = ("RS256",)


@dataclass(frozen=True)
class ValidatedIdentity:
    """Identity claims accepted only after OIDC signature and claim validation."""

    issuer: str
    subject: str
    email: str | None
    email_verified: bool | None
    given_name: str
    family_name: str
    claims: dict[str, Any]


def _fernet(secret: str) -> Fernet:
    if not secret or secret == "changeme-set-SESSION_SECRET_KEY" or len(secret) < 32:
        raise ValueError("SESSION_SECRET_KEY must be a non-default secret of at least 32 characters")
    key_material = hashlib.sha256(b"pygarden-oneid-oidc-v1:" + secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key_material))


def _is_secure_or_loopback(url: str) -> bool:
    """Allow HTTPS endpoints and HTTP only on loopback for local tests."""
    parsed = urlsplit(url)
    if parsed.scheme == "https" and parsed.hostname:
        return True
    if parsed.scheme != "http" or not parsed.hostname:
        return False
    if parsed.hostname.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        return False


def _redirect_is_local_path(value: str) -> bool:
    parsed = urlsplit(value)
    return (
        value.startswith("/")
        and not value.startswith("//")
        and parsed.scheme == ""
        and parsed.netloc == ""
        and "\\" not in value
        and "\r" not in value
        and "\n" not in value
    )


def begin_login(
    *,
    client_id: str,
    client_secret: str | None,
    authorization_endpoint: str,
    redirect_uri: str,
    session_secret: str,
    secure_cookie: bool,
    response: Response,
    return_to: str = "/",
) -> str:
    """Create an OIDC authorization URL and set an encrypted transaction cookie."""
    if not _is_secure_or_loopback(authorization_endpoint) or not _is_secure_or_loopback(redirect_uri):
        raise HTTPException(status_code=500, detail="OIDC endpoints must use HTTPS")
    if not _redirect_is_local_path(return_to):
        raise HTTPException(status_code=400, detail="Invalid post-login redirect")
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    challenge = challenge.rstrip(b"=").decode("ascii")
    oauth = OAuth2Session(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope="openid profile email",
        code_challenge_method="S256",
    )
    url, _ = oauth.create_authorization_url(
        authorization_endpoint,
        state=state,
        code_verifier=verifier,
        nonce=nonce,
        code_challenge=challenge,
        code_challenge_method="S256",
    )
    transaction = (
        _fernet(session_secret)
        .encrypt(json.dumps({"state": state, "nonce": nonce, "verifier": verifier, "return_to": return_to}).encode())
        .decode()
    )
    response.set_cookie(
        TRANSACTION_COOKIE,
        transaction,
        max_age=TRANSACTION_MAX_AGE_SECONDS,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        path=urlsplit(redirect_uri).path or "/",
    )
    return url


def clear_transaction_cookie(response: Response, *, redirect_uri: str, secure_cookie: bool) -> None:
    """Clear the short-lived authorization transaction cookie."""
    response.delete_cookie(
        TRANSACTION_COOKIE,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        path=urlsplit(redirect_uri).path or "/",
    )


def _read_transaction(request: Request, session_secret: str, state: str) -> dict[str, str]:
    signed = request.cookies.get(TRANSACTION_COOKIE)
    if not signed:
        raise HTTPException(status_code=401, detail="Missing OIDC login transaction")
    try:
        decoded = _fernet(session_secret).decrypt(signed.encode(), ttl=TRANSACTION_MAX_AGE_SECONDS)
        data = json.loads(decoded)
    except (InvalidToken, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired OIDC transaction") from exc
    if not isinstance(data, dict) or not isinstance(data.get("state"), str):
        raise HTTPException(status_code=401, detail="Invalid OIDC transaction")
    if not hmac.compare_digest(data["state"], state):
        raise HTTPException(status_code=401, detail="OIDC state validation failed")
    for field in ("nonce", "verifier", "return_to"):
        if not isinstance(data.get(field), str):
            raise HTTPException(status_code=401, detail="Invalid OIDC transaction")
    if not _redirect_is_local_path(data["return_to"]):
        raise HTTPException(status_code=401, detail="Invalid OIDC redirect")
    return data


def _fetch_token(
    *,
    token_endpoint: str,
    client_id: str,
    client_secret: str | None,
    redirect_uri: str,
    code: str,
    verifier: str,
) -> dict[str, Any]:
    oauth = OAuth2Session(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope="openid profile email",
        code_challenge_method="S256",
    )
    token = oauth.fetch_token(
        token_endpoint,
        grant_type="authorization_code",
        code=code,
        redirect_uri=redirect_uri,
        code_verifier=verifier,
        timeout=10,
    )
    if not isinstance(token, dict):
        raise HTTPException(status_code=401, detail="Invalid OIDC token response")
    return token


def _resolve_signing_key(header: dict[str, Any], jwks: dict[str, Any]) -> Any:
    """Return the unique configured RSA verification key for an ID-token header."""
    algorithm = header.get("alg")
    key_id = header.get("kid")
    if (
        algorithm not in APPROVED_ID_TOKEN_ALGORITHMS
        or not isinstance(key_id, str)
        or not key_id.strip()
        or "crit" in header
        or header.get("b64") is False
    ):
        raise HTTPException(status_code=401, detail="Unapproved OIDC signing key")
    jwk_entries = jwks.get("keys") if isinstance(jwks, dict) else None
    if not isinstance(jwk_entries, list):
        raise HTTPException(status_code=401, detail="Invalid OIDC key set")
    raw_matches = [entry for entry in jwk_entries if isinstance(entry, dict) and entry.get("kid") == key_id]
    if len(raw_matches) != 1:
        raise HTTPException(status_code=401, detail="Unknown OIDC signing key")
    raw_key = raw_matches[0]
    key_ops = raw_key.get("key_ops")
    if (
        raw_key.get("kty") != "RSA"
        or raw_key.get("alg", algorithm) != algorithm
        or raw_key.get("use", "sig") != "sig"
        or (key_ops is not None and (not isinstance(key_ops, list) or "verify" not in key_ops))
    ):
        raise HTTPException(status_code=401, detail="Unapproved OIDC signing key")
    keyset = jwt.PyJWKSet.from_dict(jwks)
    matches = [
        key for key in keyset.keys if key.key_id == key_id and key.algorithm_name == algorithm and key.key_type == "RSA"
    ]
    if len(matches) != 1:
        raise HTTPException(status_code=401, detail="Unknown OIDC signing key")
    return matches[0].key


def _validate_id_token(
    encoded: str,
    *,
    jwks: dict[str, Any],
    issuer: str,
    client_id: str,
    nonce: str,
) -> ValidatedIdentity:
    """Verify the signed ID token and validate required OIDC identity claims."""
    try:
        header = jwt.get_unverified_header(encoded)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Malformed OIDC ID token") from exc
    signing_key = _resolve_signing_key(header, jwks)
    try:
        claims = jwt.decode(
            encoded,
            signing_key,
            algorithms=list(APPROVED_ID_TOKEN_ALGORITHMS),
            issuer=issuer,
            audience=client_id,
            leeway=60,
            options={"require": ["iss", "sub", "aud", "exp", "iat", "nonce"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="OIDC ID token validation failed") from exc
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise HTTPException(status_code=401, detail="OIDC subject is missing")
    token_nonce = claims.get("nonce")
    if not isinstance(token_nonce, str) or not hmac.compare_digest(token_nonce, nonce):
        raise HTTPException(status_code=401, detail="OIDC nonce validation failed")
    audiences = claims.get("aud")
    authorized_party = claims.get("azp")
    if authorized_party is not None and authorized_party != client_id:
        raise HTTPException(status_code=401, detail="OIDC authorized party validation failed")
    if isinstance(audiences, list) and len(audiences) > 1 and authorized_party != client_id:
        raise HTTPException(status_code=401, detail="OIDC authorized party validation failed")
    return ValidatedIdentity(
        issuer=issuer,
        subject=subject,
        email=claims.get("email") if isinstance(claims.get("email"), str) else None,
        email_verified=(claims.get("email_verified") if isinstance(claims.get("email_verified"), bool) else None),
        given_name=claims.get("given_name", "") if isinstance(claims.get("given_name", ""), str) else "",
        family_name=claims.get("family_name", "") if isinstance(claims.get("family_name", ""), str) else "",
        claims=claims,
    )


async def validate_callback(
    request: Request,
    *,
    code: str,
    state: str,
    issuer: str,
    client_id: str,
    client_secret: str | None,
    token_endpoint: str,
    jwks_uri: str,
    redirect_uri: str,
    session_secret: str,
) -> ValidatedIdentity:
    """Exchange a callback code and return only a fully validated OIDC identity."""
    if any(not _is_secure_or_loopback(endpoint) for endpoint in (issuer, token_endpoint, jwks_uri, redirect_uri)):
        raise HTTPException(status_code=500, detail="OIDC endpoints must use HTTPS")
    transaction = _read_transaction(request, session_secret, state)
    try:
        token = await asyncio.to_thread(
            _fetch_token,
            token_endpoint=token_endpoint,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            code=code,
            verifier=transaction["verifier"],
        )
        id_token = token.get("id_token")
        if not isinstance(id_token, str) or not id_token:
            raise HTTPException(status_code=401, detail="OIDC response has no ID token")
        response = await asyncio.to_thread(requests.get, jwks_uri, timeout=10)
        response.raise_for_status()
        return _validate_id_token(
            id_token,
            jwks=response.json(),
            issuer=issuer,
            client_id=client_id,
            nonce=transaction["nonce"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="OIDC authentication failed") from exc


def callback_return_to(request: Request, session_secret: str, state: str) -> str:
    """Read the already validated transaction's local post-login path."""
    return _read_transaction(request, session_secret, state)["return_to"]


def get_configured_oidc_values() -> dict[str, Any]:
    """Return configured OneID endpoints for the legacy pyGARDEN router."""
    return {
        "issuer": config.ONEID_ISSUER,
        "client_id": config.ONEID_CLIENT,
        "client_secret": config.ONEID_CLIENT_SECRET or None,
        "authorization_endpoint": config.ONEID_AUTH_URL,
        "token_endpoint": config.ONEID_TOKEN_URL,
        "jwks_uri": config.ONEID_JWKS_URL,
        "session_secret": config.SESSION_SECRET_KEY,
        "secure_cookie": config.SESSION_COOKIE_SECURE,
    }
