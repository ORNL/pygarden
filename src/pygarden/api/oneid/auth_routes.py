
import jwt
import requests
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from jwt import PyJWKClient
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from . import *
from .auth_db import AuthDB

ONEID_CLIENT = os.getenv("ONEID_CLIENT", "ornlHEXUS")
ENVIRON = os.getenv("ENVIRON", "dev")

router = APIRouter()

@router.get("/login/oauth2/code/oneid")
async def login_oauth2_code_oneid(code: str, request: Request) -> Response:
    if get_auth_mode() != AUTH_MODE_ONEID:
        raise HTTPException(status_code=404, detail="OneID login is disabled.")

    async with AuthDB() as adb:
        redirect_url = "/"
        if request.cookies.get("redirect_after_login"):
            redirect_url = request.cookies.get("redirect_after_login")
        response = RedirectResponse(url=redirect_url)
        if request.cookies.get("redirect_after_login"):
            response.delete_cookie("redirect_after_login")
        jwks_client = PyJWKClient("https://eams-auth.oneid.energy.gov/ext/oauth/jwks")
        jwt_resp = requests.post("https://eams-auth.oneid.energy.gov/as/token.oauth2",
                                data={
                                    "grant_type": "authorization_code",
                                    "code": code,
                                    "redirect_uri": get_oauth_redirect_uri(request),
                                    "client_id": ONEID_CLIENT,
                                },
                                timeout=15)
        token = jwt_resp.json().get("access_token")
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        jwt_data = jwt.decode(token, signing_key.key, algorithms=["RS256"], options={"verify_signature": False if ENVIRON == "dev" else True})
        email = normalize_email(jwt_data.get("email"))
        if not email:
            raise HTTPException(status_code=401, detail="OneID response did not include an email address.")
        email_status = await adb.getEmailStatus(email)
        session = uuid4()
        session_data = SessionData(
            user_id=-1,
            email=email,
            first_name=jwt_data.get("given_name"),
            last_name=jwt_data.get("family_name"),
            us_citizen=bool(jwt_data.get("us_citizen", False)),
            affiliation=f"{jwt_data.get('doe_affiliation_level_1', '')}/{jwt_data.get('doe_affiliation_level_2', '')}",
            admin=False,
        )
        if email_status == "active":
            user = await adb.getUserByEmail(email)
            session_data.user_id = user["user_id"]
            session_data.admin = user.get("admin", False)
            await backend.create(session, session_data)
            cookie.attach_to_response(response, session)
        elif email_status == "disabled":
            response = RedirectResponse(url="/account-status?status=disabled")
        elif email_status == "unapproved":
            response = RedirectResponse(url="/account-status?status=unapproved")
        else:
            await adb.createUser(
                email=email,
                first_name=jwt_data.get("given_name"),
                last_name=jwt_data.get("family_name"),
                us_citizen=bool(jwt_data.get("us_citizen", False)),
                affiliation=f"{jwt_data.get('doe_affiliation_level_1', '')}/{jwt_data.get('doe_affiliation_level_2', '')}",
            )
            await send_new_user_email(session_data, request)
            response = RedirectResponse(url="/account-status?status=created")
        return response

@router.get("/logout")
async def logout(session_id: UUID = Depends(cookie)):
    await backend.delete(session_id)
    response = RedirectResponse(url="/account-status?status=logged_out")
    cookie.delete_from_response(response)
    return response

@router.get("/approve-user")
async def approve_user(email: str, user: SessionData = Depends(get_user)):
    async with AuthDB() as adb:
        if not user.admin:
            return RedirectResponse(url="/account-status?status=unauthorized", status_code=302)
        normalized_email = normalize_email(email)
        await adb.approveUser(normalized_email)
        return f"User {normalized_email} approved"


@router.get("/user-info")
def user_info(user: SessionData = Depends(get_user)):
    return user

@router.get("/login-url")
def login_url(request: Request):
    return get_login_url(request)
