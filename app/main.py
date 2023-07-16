from uvicorn.workers import UvicornWorker

from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import PlainTextResponse, JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import Request

from .config import DEBUG, PREFIX, db
from .routes import (
    annotation,
    text,
    texts,
    user,
    series,
    search,
    xml,
    arethusa,
    stats,
    chapter,
    zotero,
    aows,
    tests,
    person,
    smyth,
)
from .jwt import JWTAuthBackend


def on_auth_error(request: Request, exc: Exception):
    return JSONResponse({"ok": False, "error": str(exc)}, status_code=401)


app = Starlette(
    routes=[
        Route(f"{PREFIX}/", lambda: PlainTextResponse("API")),
        Mount(f"{PREFIX}/user", routes=user.routes),
        Mount(f"{PREFIX}/texts", routes=texts.routes),
        Mount(f"{PREFIX}/text", routes=text.routes),
        Mount(f"{PREFIX}/annotation", routes=annotation.routes),
        Mount(f"{PREFIX}/series", routes=series.routes),
        Mount(f"{PREFIX}/search", routes=search.routes),
        Mount(f"{PREFIX}/xml", routes=xml.routes),
        Mount(f"{PREFIX}/arethusa", routes=arethusa.routes),
        Mount(f"{PREFIX}/stats", routes=stats.routes),
        Mount(f"{PREFIX}/chapter", routes=chapter.routes),
        Mount(f"{PREFIX}/zotero", routes=zotero.routes),
        Mount(f"{PREFIX}/tests", routes=tests.routes),
        Mount(f"{PREFIX}/aows", routes=aows.routes),
        Mount(f"{PREFIX}/person", routes=person.routes),
        Mount(f"{PREFIX}/smyth", routes=smyth.routes),
    ],
    debug=DEBUG,
    on_startup=[db.connect],
    on_shutdown=[db.disconnect],
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:8080",
                "http://localhost:1234",
                "https://localhost",
                "https://localhost/",
                "https://127.0.0.1:5173",
            ],
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=1,
        ),
        Middleware(GZipMiddleware),
        Middleware(
            AuthenticationMiddleware, backend=JWTAuthBackend(), on_error=on_auth_error
        ),
    ],
)


class Worker(UvicornWorker):
    CONFIG_KWARGS = {
        "root_path": PREFIX,
    }
