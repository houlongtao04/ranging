from fastapi import APIRouter, Depends, Form, Request
from sqlmodel import Session

from ..db import DEMO_PASSWORD, DEMO_USERS, get_db
from ..models import Role
from ..security import find_user, session_user
from .common import page, redirect

router = APIRouter(include_in_schema=False)


@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    user = session_user(request, db)
    if user is None:
        return redirect(request, "/login")
    return redirect(request, "/me/leaves" if user.role == Role.STUDENT else "/inbox")


@router.get("/login")
def login_form(request: Request):
    return page(request, "login.html", demo=DEMO_USERS, demo_pw=DEMO_PASSWORD)


@router.post("/login")
def login_submit(request: Request, account: str = Form(""), password: str = Form(""),
                 db: Session = Depends(get_db)):
    user = find_user(db, account, password)
    if user is None:
        return page(request, "login.html", 400, demo=DEMO_USERS, demo_pw=DEMO_PASSWORD,
                    error="帳號或密碼錯誤，請再試一次", account=account)
    request.session["uid"] = user.id
    return redirect(request, "/", f"歡迎回來，{user.display_name}")


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return redirect(request, "/login", "已登出")
