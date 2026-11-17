import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from .api import auth, student, teacher
from .db import init_db
from .security import NotLoggedIn
from .web import account_views, student_views, teacher_views
from .web.common import page


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="線上請假系統", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("APP_SECRET", "change-me"),
                   max_age=60 * 60 * 8)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

for r in (auth.router, student.router, teacher.router,
          account_views.router, student_views.router, teacher_views.router):
    app.include_router(r)


def wants_json(request: Request) -> bool:
    return request.url.path.startswith("/api/")


@app.exception_handler(NotLoggedIn)
async def not_logged_in(request: Request, _: NotLoggedIn):
    if wants_json(request):
        return JSONResponse({"detail": "尚未登入"}, status_code=401)
    request.session["notice"] = {"text": "請先登入", "kind": "warn"}
    return RedirectResponse("/login", status_code=303)


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    if wants_json(request):
        return await http_exception_handler(request, exc)
    return page(request, "error.html", exc.status_code, err_code=exc.status_code, msg=exc.detail)
