"""Small local OIDC authorization-code provider for protocol integration tests."""

# Test protocol handler complexity and private test helper methods are intentional.
# ruff: noqa: C901,D102,D105,D107

import base64
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit

import jwt
import requests
from cryptography.hazmat.primitives.asymmetric import rsa


def _b64url(number: int) -> str:
    length = (number.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(number.to_bytes(length, "big")).rstrip(b"=").decode()


class LocalOIDCProvider:
    """Local issuer with discovery, authorization, token, and JWKS endpoints."""

    def __init__(self):
        self.issuer = ""
        self.client_id = "esdx-test-client"
        self.client_secret = "test-client-secret"
        self.good_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.bad_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.pending_codes: dict[str, dict] = {}
        self.scenario = "valid"
        self.lock = threading.Lock()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, _format, *_args):
                return

            def _json(self, status: int, payload: dict):
                body = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                parsed = urlsplit(self.path)
                if parsed.path == "/.well-known/openid-configuration":
                    return self._json(
                        200,
                        {
                            "issuer": owner.issuer,
                            "authorization_endpoint": f"{owner.issuer}/authorize",
                            "token_endpoint": f"{owner.issuer}/token",
                            "jwks_uri": f"{owner.issuer}/jwks",
                            "response_types_supported": ["code"],
                            "subject_types_supported": ["public"],
                            "id_token_signing_alg_values_supported": ["RS256"],
                            "token_endpoint_auth_methods_supported": ["client_secret_basic"],
                            "code_challenge_methods_supported": ["S256"],
                        },
                    )
                if parsed.path == "/jwks":
                    public = owner.good_key.public_key().public_numbers()
                    return self._json(
                        200,
                        {
                            "keys": [
                                {
                                    "kty": "RSA",
                                    "use": "sig",
                                    "alg": "RS256",
                                    "kid": "good-key",
                                    "n": _b64url(public.n),
                                    "e": _b64url(public.e),
                                }
                            ]
                        },
                    )
                if parsed.path == "/authorize":
                    query = parse_qs(parsed.query)
                    required = (
                        "response_type",
                        "client_id",
                        "redirect_uri",
                        "state",
                        "nonce",
                        "code_challenge",
                        "code_challenge_method",
                        "scope",
                    )
                    if any(not query.get(key) for key in required):
                        return self._json(400, {"error": "invalid_request"})
                    if (
                        query["response_type"][0] != "code"
                        or query["client_id"][0] != owner.client_id
                        or query["code_challenge_method"][0] != "S256"
                        or "openid" not in query["scope"][0].split()
                    ):
                        return self._json(400, {"error": "invalid_request"})
                    code = f"one-use-{time.time_ns()}"
                    with owner.lock:
                        scenario, owner.scenario = owner.scenario, "valid"
                        owner.pending_codes[code] = {
                            "redirect_uri": query["redirect_uri"][0],
                            "state": query["state"][0],
                            "nonce": query["nonce"][0],
                            "challenge": query["code_challenge"][0],
                            "scenario": scenario,
                        }
                    target = query["redirect_uri"][0] + "?" + urlencode({"code": code, "state": query["state"][0]})
                    self.send_response(302)
                    self.send_header("Location", target)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                return self._json(404, {"error": "not_found"})

            def do_POST(self):
                if urlsplit(self.path).path != "/token":
                    return self._json(404, {"error": "not_found"})
                length = int(self.headers.get("Content-Length", "0"))
                form = parse_qs(self.rfile.read(length).decode())
                code = form.get("code", [""])[0]
                with owner.lock:
                    data = owner.pending_codes.pop(code, None)
                if data is None:
                    return self._json(400, {"error": "invalid_grant"})
                verifier = form.get("code_verifier", [""])[0]
                challenge = (
                    base64.urlsafe_b64encode(__import__("hashlib").sha256(verifier.encode()).digest())
                    .rstrip(b"=")
                    .decode()
                )
                if (
                    form.get("grant_type") != ["authorization_code"]
                    or form.get("redirect_uri") != [data["redirect_uri"]]
                    or challenge != data["challenge"]
                    or self.headers.get("Authorization")
                    != "Basic " + base64.b64encode(f"{owner.client_id}:{owner.client_secret}".encode()).decode()
                ):
                    return self._json(400, {"error": "invalid_grant"})
                now = int(time.time())
                scenario = data["scenario"]
                claims = {
                    "iss": owner.issuer,
                    "sub": "researcher-subject",
                    "aud": owner.client_id,
                    "iat": now,
                    "exp": now + 300,
                    "nonce": data["nonce"],
                    "email": "researcher@example.invalid",
                    "email_verified": True,
                    "given_name": "OIDC",
                    "family_name": "Researcher",
                }
                if scenario == "wrong_issuer":
                    claims["iss"] = owner.issuer + "/untrusted"
                elif scenario == "wrong_audience":
                    claims["aud"] = "another-client"
                elif scenario == "expired":
                    # Deliberately exceed the verifier's allowed clock-skew leeway.
                    claims["exp"] = now - 300
                elif scenario == "missing_nonce":
                    claims.pop("nonce")
                elif scenario == "wrong_nonce":
                    claims["nonce"] = "wrong-nonce"
                elif scenario == "missing_subject":
                    claims.pop("sub")
                elif scenario == "changed_email":
                    claims["email"] = "changed@example.invalid"
                elif scenario == "duplicate_email":
                    claims["sub"] = "second-subject"
                signing_key = owner.bad_key if scenario == "bad_signature" else owner.good_key
                kid = "bad-key" if scenario == "bad_signature" else "good-key"
                id_token = jwt.encode(claims, signing_key, algorithm="RS256", headers={"kid": kid})
                token = {
                    "access_token": "this-is-not-the-id-token",
                    "token_type": "Bearer",
                    "expires_in": 300,
                    "id_token": id_token,
                }
                if scenario == "missing_id_token":
                    token.pop("id_token")
                return self._json(200, token)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.issuer = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()
        return self

    def __enter__(self):
        return self.start()

    def __exit__(self, _exc_type, _exc, _traceback):
        self.close()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def authorize(self, url: str) -> dict[str, str]:
        response = requests.get(url, allow_redirects=False, timeout=5)
        if response.status_code != 302:
            raise AssertionError(f"OIDC authorization failed: {response.status_code}")
        return {key: values[0] for key, values in parse_qs(urlsplit(response.headers["Location"]).query).items()}
