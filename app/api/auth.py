from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from ..db import get_db
from ..models import User
from ..schemas import LoginBody, UserInfo
from ..security import find_user, login_user

router = APIRouter(prefix="/api/auth", tags=["登入"])


@router.post("/login", response_model=UserInfo)
def api_login(body: LoginBody, request: Request, db: Session = Depends(get_db)):
    user = find_user(db, body.account, body.password)
    if user is None:
        raise HTTPException(401, "帳號或密碼錯誤")
    request.session["uid"] = user.id
    return UserInfo.from_user(user)


@router.post("/logout")
def api_logout(request: Request):
    request.session.clear()
    return {"message": "已登出"}


@router.get("/me", response_model=UserInfo)
def api_me(user: User = Depends(login_user)):
    return UserInfo.from_user(user)
