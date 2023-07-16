import jwt

from google.oauth2 import id_token
from google.auth.transport import requests

from starlette.routing import Route
from starlette.authentication import requires

from ..response import JSONResponse
from .. import config
from ..config import db


async def tokensignin(request):
    body = await request.json()
    token = body["token"]
    user = id_token.verify_oauth2_token(
        token, requests.Request(), config.GOOGLE_CLIENT_ID
    )
    try:
        user = id_token.verify_oauth2_token(
            token, requests.Request(), config.GOOGLE_CLIENT_ID
        )
    except:
        return JSONResponse({"ok": False, "result": "Invalid token"}, status_code=403)

    if not user["email_verified"]:
        return JSONResponse(
            {"ok": False, "result": "Nonverified email"}, status_code=403
        )

    db_user = await db.fetch_one(
        """
        SELECT * 
          FROM user
         WHERE email = %(email)s
        """,
        {"email": user["email"]},
    )

    db_user = db_user["result"]

    if db_user:
        user["level"] = db_user["level"]
        user["id"] = db_user["id"]
    else:
        try:
            result = await db.execute(
                """
                INSERT INTO user (email, name, level) 
                VALUES (%(email)s, %(name)s, 0)
                """,
                {"email": user["email"], "name": user["name"]},
            )

            user["level"] = 0
            user["id"] = result["result"]["lastrowid"]

        except:
            return JSONResponse(
                {"ok": False, "result": "Could not add user"}, status_code=403
            )
    if user["level"] == 0:
        user["level"] = ["user"]
    elif user["level"] == 1:
        user["level"] = ["user", "editor"]
    elif user["level"] == 2:
        user["level"] = ["user", "editor", "admin"]
    return JSONResponse(
        {"token": jwt.encode(user, config.JWT_SECRET, algorithm="HS256"), "user": user}
    )


@requires("user")
async def me(request):
    user = request.user
    return JSONResponse(
        {"email": user.email, "name": user.name, "level": user.level, "id": user.id}
    )


@requires("user")
async def ping(request):
    return JSONResponse({"ok": True, "result": ""})


@requires("editor")
async def ping_editor(request):
    return JSONResponse({"ok": True, "result": ""})


@requires("admin")
async def ping_admin(request):
    return JSONResponse({"ok": True, "result": ""})


routes = [
    Route("/tokensignin", tokensignin, methods=["POST"]),
    Route("/me", me),
    Route("/ping/editor", ping_editor),
    Route("/ping/admin", ping_admin),
    Route("/ping", ping),
]
