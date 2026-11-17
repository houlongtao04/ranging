from pathlib import Path

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from ..models import LEAVE_TYPES, MAX_DAYS, REASON_LIMIT, LeaveStatus

templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")
templates.env.globals.update(LeaveStatus=LeaveStatus, LEAVE_TYPES=LEAVE_TYPES,
                             MAX_DAYS=MAX_DAYS, REASON_LIMIT=REASON_LIMIT)

WEEKDAYS = "一二三四五六日"


def show_date(d):
    return f"{d.month}/{d.day}（{WEEKDAYS[d.weekday()]}）"


templates.env.filters["md"] = show_date


def page(request: Request, name: str, code: int = 200, **ctx):
    ctx["notice"] = request.session.pop("notice", None)
    return templates.TemplateResponse(request, name, ctx, status_code=code)


def redirect(request: Request, to: str, notice: str = "", kind: str = "ok"):
    if notice:
        request.session["notice"] = {"text": notice, "kind": kind}
    return RedirectResponse(to, status_code=303)
