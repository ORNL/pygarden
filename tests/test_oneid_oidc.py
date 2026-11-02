"""OIDC regression tests against a local authorization-code provider."""

# The tests use concise names and fixture helpers; production modules keep the
# package's strict docstring checks.
# ruff: noqa: D103

import asyncio
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import HTTPException, Response
from oidc_provider import LocalOIDCProvider
from starlette.requests import Request

from pygarden.api.oneid.oidc import (
    TRANSACTION_COOKIE,
    begin_login,
    validate_callback,
)

SESSION_SECRET = "oidc-test-session-secret-at-least-32-bytes"
CLIENT_ID = "esdx-test-client"
CLIENT_SECRET = "test-client-secret"
REDIRECT_URI = "http://127.0.0.1/callback"


@pytest.fixture
def provider():
    instance = LocalOIDCProvider().start()
    try:
        yield instance
    finally:
        instance.close()


def start_transaction(provider: LocalOIDCProvider):
    response = Response()
    authorization_url = begin_login(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        authorization_endpoint=f"{provider.issuer}/authorize",
        redirect_uri=REDIRECT_URI,
        session_secret=SESSION_SECRET,
        secure_cookie=False,
        response=response,
        return_to="/profile",
    )
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    transaction_cookie = cookie[TRANSACTION_COOKIE].value
    callback = provider.authorize(authorization_url)
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "http",
            "path": "/callback",
            "query_string": b"",
            "headers": [
                (b"cookie", f"{TRANSACTION_COOKIE}={transaction_cookie}".encode()),
            ],
            "server": ("client.test", 80),
            "client": ("127.0.0.1", 12345),
        }
    )
    return request, callback


def validate(provider: LocalOIDCProvider, request: Request, callback: dict[str, str]):
    return asyncio.run(
        validate_callback(
            request,
            code=callback["code"],
            state=callback["state"],
            issuer=provider.issuer,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            token_endpoint=f"{provider.issuer}/token",
            jwks_uri=f"{provider.issuer}/jwks",
            redirect_uri=REDIRECT_URI,
            session_secret=SESSION_SECRET,
        )
    )


def test_transaction_cookie_encrypts_state_and_pkce_verifier(provider):
    response = Response()
    authorization_url = begin_login(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        authorization_endpoint=f"{provider.issuer}/authorize",
        redirect_uri=REDIRECT_URI,
        session_secret=SESSION_SECRET,
        secure_cookie=False,
        response=response,
        return_to="/private/research",
    )
    authorization_query = parse_qs(urlsplit(authorization_url).query)
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    transaction = cookie[TRANSACTION_COOKIE].value
    assert authorization_query["state"][0] not in transaction
    assert authorization_query["nonce"][0] not in transaction
    assert "/private/research" not in transaction
    assert "verifier" not in transaction


def test_valid_oidc_login_uses_id_token_and_pkce(provider):
    request, callback = start_transaction(provider)
    identity = validate(provider, request, callback)
    assert identity.issuer == provider.issuer
    assert identity.subject == "researcher-subject"
    assert identity.email == "researcher@example.invalid"


@pytest.mark.parametrize(
    "scenario",
    [
        "wrong_issuer",
        "wrong_audience",
        "bad_signature",
        "expired",
        "missing_nonce",
        "wrong_nonce",
        "missing_subject",
        "missing_id_token",
    ],
)
def test_untrusted_or_malformed_id_tokens_are_rejected(provider, scenario):
    provider.scenario = scenario
    request, callback = start_transaction(provider)
    with pytest.raises(HTTPException) as error:
        validate(provider, request, callback)
    assert error.value.status_code == 401


def test_invalid_state_does_not_exchange_code_or_return_identity(provider):
    request, callback = start_transaction(provider)
    invalid_callback = {**callback, "state": callback["state"] + "x"}
    with pytest.raises(HTTPException, match="state"):
        validate(provider, request, invalid_callback)
    assert validate(provider, request, callback).subject == "researcher-subject"


def test_callback_code_replay_is_rejected_by_token_endpoint(provider):
    request, callback = start_transaction(provider)
    assert validate(provider, request, callback).subject == "researcher-subject"
    with pytest.raises(HTTPException):
        validate(provider, request, callback)


def test_email_changes_and_duplicate_email_do_not_change_identity_keys(provider):
    request, callback = start_transaction(provider)
    first = validate(provider, request, callback)

    provider.scenario = "changed_email"
    request, callback = start_transaction(provider)
    changed_email = validate(provider, request, callback)
    assert (changed_email.issuer, changed_email.subject) == (first.issuer, first.subject)
    assert changed_email.email == "changed@example.invalid"

    provider.scenario = "duplicate_email"
    request, callback = start_transaction(provider)
    second_subject = validate(provider, request, callback)
    assert second_subject.email == "researcher@example.invalid"
    assert second_subject.subject != first.subject


def test_post_login_redirect_rejects_external_urls(provider):
    response = Response()
    with pytest.raises(HTTPException, match="redirect"):
        begin_login(
            client_id=CLIENT_ID,
            client_secret=None,
            authorization_endpoint=f"{provider.issuer}/authorize",
            redirect_uri=REDIRECT_URI,
            session_secret=SESSION_SECRET,
            secure_cookie=False,
            response=response,
            return_to="https://attacker.invalid/",
        )
