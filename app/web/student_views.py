from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlmodel import Session

from .. import leave_service as svc
from ..db import get_db
from ..models import LeaveStatus, User
from ..security import student_only
from .common import page, redirect

router = APIRouter(prefix="/me/leaves", include_in_schema=False)


@router.get("")
def my_list(request: Request, show: str = "all", me: User = Depends(student_only),
            db: Session = Depends(get_db)):
    leaves = svc.my_leaves(db, me)
    stats = {s.value: 0 for s in LeaveStatus}
    for x in leaves:
        stats[x.status.value] += 1
    shown = leaves if show not in stats else [x for x in leaves if x.status.value == show]
    return page(request, "student/list.html", me=me, leaves=shown, stats=stats,
                total=len(leaves), show=show if show in stats else "all",
                used_days=svc.approved_days(leaves))


def _blank():
    today = date.today().isoformat()
    return {"leave_type": "病假", "start_date": today, "end_date": today, "reason": ""}


@router.get("/new")
def new_form(request: Request, me: User = Depends(student_only)):
    return page(request, "student/form.html", me=me, leave=None, f=_blank())


@router.post("/new")
def new_save(request: Request, leave_type: str = Form(""), start_date: str = Form(""),
             end_date: str = Form(""), reason: str = Form(""), then: str = Form("save"),
             me: User = Depends(student_only), db: Session = Depends(get_db)):
    f = dict(leave_type=leave_type, start_date=start_date, end_date=end_date, reason=reason)
    try:
        leave = svc.create_leave(db, me, svc.LeaveForm(**f))
    except HTTPException as e:
        return page(request, "student/form.html", 400, me=me, leave=None, f=f, error=e.detail)
    if then == "send":
        return _send(request, db, me, leave.id)
    return redirect(request, f"/me/leaves/{leave.id}", "假單已存成草稿")


@router.get("/{leave_id}")
def detail(request: Request, leave_id: int, me: User = Depends(student_only),
           db: Session = Depends(get_db)):
    leave = svc.my_leave(db, me, leave_id)
    return page(request, "student/detail.html", me=me, leave=leave,
                logs=svc.logs_of(db, leave.id))


@router.get("/{leave_id}/edit")
def edit_form(request: Request, leave_id: int, me: User = Depends(student_only),
              db: Session = Depends(get_db)):
    leave = svc.my_leave(db, me, leave_id)
    if leave.status not in svc.EDITABLE:
        return redirect(request, f"/me/leaves/{leave.id}", "這張假單目前不能修改", "warn")
    f = dict(leave_type=leave.leave_type, start_date=leave.start_date.isoformat(),
             end_date=leave.end_date.isoformat(), reason=leave.reason)
    return page(request, "student/form.html", me=me, leave=leave, f=f)


@router.post("/{leave_id}/edit")
def edit_save(request: Request, leave_id: int, leave_type: str = Form(""),
              start_date: str = Form(""), end_date: str = Form(""), reason: str = Form(""),
              then: str = Form("save"), me: User = Depends(student_only),
              db: Session = Depends(get_db)):
    f = dict(leave_type=leave_type, start_date=start_date, end_date=end_date, reason=reason)
    try:
        svc.edit_leave(db, me, leave_id, svc.LeaveForm(**f))
    except HTTPException as e:
        if e.status_code != 400:
            raise
        leave = svc.my_leave(db, me, leave_id)
        return page(request, "student/form.html", 400, me=me, leave=leave, f=f, error=e.detail)
    if then == "send":
        return _send(request, db, me, leave_id)
    return redirect(request, f"/me/leaves/{leave_id}", "修改已儲存")


def _send(request, db, me, leave_id):
    try:
        svc.send_leave(db, me, leave_id)
    except HTTPException as e:
        if e.status_code != 409:
            raise
        return redirect(request, f"/me/leaves/{leave_id}", e.detail, "warn")
    return redirect(request, "/me/leaves", "已送出，等導師審核")


@router.post("/{leave_id}/send")
def send(request: Request, leave_id: int, me: User = Depends(student_only),
         db: Session = Depends(get_db)):
    return _send(request, db, me, leave_id)


@router.post("/{leave_id}/withdraw")
def withdraw(request: Request, leave_id: int, me: User = Depends(student_only),
             db: Session = Depends(get_db)):
    try:
        svc.withdraw_leave(db, me, leave_id)
    except HTTPException as e:
        if e.status_code != 409:
            raise
        return redirect(request, f"/me/leaves/{leave_id}", e.detail, "warn")
    return redirect(request, f"/me/leaves/{leave_id}", "已撤回，假單回到草稿")


@router.post("/{leave_id}/delete")
def delete(request: Request, leave_id: int, me: User = Depends(student_only),
           db: Session = Depends(get_db)):
    try:
        svc.remove_leave(db, me, leave_id)
    except HTTPException as e:
        if e.status_code != 409:
            raise
        return redirect(request, f"/me/leaves/{leave_id}", e.detail, "warn")
    return redirect(request, "/me/leaves", "草稿已刪除")
