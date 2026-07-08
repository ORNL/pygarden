import os
from uuid import UUID

from fastapi import HTTPException, Request
from fastapi_sessions.frontends.implementations import CookieParameters, SessionCookie

from .basic_verifier import BasicVerifier
from .db_backend import DBBackend
from .session_data import SessionData
from .simple_auth import AUTH_MODE_ONEID, get_auth_mode
from .auth_db import AuthDB
from pygarden.mail import send_email

ONEID_CLIENT = os.getenv("ONEID_CLIENT", "ornlHEXUS")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "HexusSecretKey")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() in {"1", "true", "yes", "on"}


class RequiresLoginException(Exception):
    pass

### SESSION SETUP ###
cookie_params = CookieParameters(secure=SESSION_COOKIE_SECURE, samesite="lax")

cookie = SessionCookie(
    cookie_name="cookie",
    identifier="general_verifier",
    auto_error=True,
    secret_key=SESSION_SECRET_KEY,
    cookie_params=cookie_params,
)

backend = DBBackend[UUID, SessionData]()

verifier = BasicVerifier(
    identifier="general_verifier",
    auto_error=True,
    backend=backend,
    auth_http_exception=HTTPException(status_code=403, detail="invalid session"),
)
### ENF OF SESSION SETUP ###


def get_public_base_url(request: Request) -> str:
    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL

    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    forwarded_port = request.headers.get("x-forwarded-port")

    scheme = (forwarded_proto or request.url.scheme or "http").split(",")[0].strip()
    host = (forwarded_host or request.headers.get("host") or request.url.hostname or "").split(",")[0].strip()
    port = (forwarded_port or "").split(",")[0].strip()

    if host and ":" not in host and port and port not in {"80", "443"}:
        host = f"{host}:{port}"

    return f"{scheme}://{host}".rstrip("/")


def get_oauth_redirect_uri(request: Request) -> str:
    return f"{get_public_base_url(request)}/login/oauth2/code/oneid"

async def send_new_user_email(new_user: SessionData, request: Request) -> None:
    async with AuthDB() as adb:
        admin_emails = await adb.get_admin_emails()
        if not admin_emails:
            return
        send_email("New HEXUS User", f"""
Hexus Admin,
               
A new user has registered for HEXUS with the following details:
- Name: {new_user.first_name} {new_user.last_name}
- Email: {new_user.email}
- Affiliation: {new_user.affiliation}
- U.S. Citizen: {"Yes" if new_user.us_citizen else "No"}

If this user should be approved, please click the following link to approve their account:
{get_public_base_url(request)}/api/approve-user?email={new_user.email}

- Hexus System
""", recipients=",".join(admin_emails))


async def send_password_reset_request_email(email: str, request: Request, name: str = "") -> None:
    async with AuthDB() as adb:
        admin_emails = await adb.get_admin_emails()
        if not admin_emails:
            return

        display_name = name.strip() or email
        send_email("HEXUS Password Reset Request", f"""
Hexus Admin,

A user has requested a password reset for their HEXUS simple-login account.

- Name: {display_name}
- Email: {email}

Please open the user administration page and issue a temporary password:
{get_public_base_url(request)}/admin/users

- Hexus System
""", recipients=",".join(admin_emails))

def get_login_url(request: Request) -> str:
    if get_auth_mode() != AUTH_MODE_ONEID:
        return f"{get_public_base_url(request)}/login"

    return (
        "https://eams-auth.oneid.energy.gov/as/authorization.oauth2"
        f"?response_type=code&client_id={ONEID_CLIENT}&redirect_uri={get_oauth_redirect_uri(request)}"
    )

def get_session_id(redirect: bool = True) -> callable:
    async def _get_session_id(request: Request) -> str:
        try:
            session_id = cookie.__call__(request)
            sd = await backend.read(session_id)
            if sd.email:
                async with AuthDB() as adb:
                    email_status = await adb.getEmailStatus(sd.email)
                    if email_status == "active":
                        return str(session_id)
        except:
            if redirect:
                raise RequiresLoginException()
            raise HTTPException(status_code=401, detail="Not authorized")
    return _get_session_id

async def get_user(request: Request) -> SessionData:
    email_status = "unknown"
    try:
        session_id = cookie.__call__(request)
        sd = await backend.read(session_id)
        if sd.email:
            async with AuthDB() as adb:
                email_status = await adb.getEmailStatus(sd.email)
    except:
        raise RequiresLoginException()
    if email_status == "active":
        return sd
    elif email_status == "disabled":
        raise HTTPException(status_code=302, detail="Not authorized", headers = {"Location": "/account-status?status=disabled"} )
    elif email_status == "unapproved":
        raise HTTPException(status_code=302, detail="Not authorized", headers = {"Location": "/account-status?status=unapproved"} )
    raise RequiresLoginException()
