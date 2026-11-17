import hashlib
import hmac
import secrets

from fastapi import Depends, HTTPException, Request
from sqlmodel import Session, select

from .db import get_db
from .models import Role, User


class NotLoggedIn(Exception):
    pass


def make_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"{salt.hex()}:{key.hex()}"


def check_password(password: str, saved: str) -> bool:
    salt, key = saved.split(":")
    new_key = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)
    return hmac.compare_digest(new_key.hex(), key)


def find_user(db: Session, account: str, password: str):
    user = db.exec(select(User).where(User.account == account.strip())).first()
    if user is None or not check_password(password, user.pw_hash):
        return None
    return user


def session_user(request: Request, db: Session):
    uid = request.session.get("uid")
    return db.get(User, uid) if uid else None


def login_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = session_user(request, db)
    if user is None:
        raise NotLoggedIn()
    return user


def student_only(user: User = Depends(login_user)) -> User:
    if user.role != Role.STUDENT:
        raise HTTPException(403, "這個功能只開放給學生")
    return user


def teacher_only(user: User = Depends(login_user)) -> User:
    if user.role != Role.TEACHER:
        raise HTTPException(403, "這個功能只開放給導師")
    return user
