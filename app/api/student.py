from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from .. import leave_service as svc
from ..db import get_db
from ..models import User
from ..schemas import LeaveBody, LeaveInfo
from ..security import student_only

router = APIRouter(prefix="/api/leaves", tags=["學生"])


def _form(body: LeaveBody):
    return svc.LeaveForm(body.leave_type, body.start_date, body.end_date, body.reason)


@router.get("", response_model=list[LeaveInfo])
def list_leaves(me: User = Depends(student_only), db: Session = Depends(get_db)):
    return [LeaveInfo.from_leave(x) for x in svc.my_leaves(db, me)]


@router.post("", response_model=LeaveInfo, status_code=201)
def add_leave(body: LeaveBody, me: User = Depends(student_only), db: Session = Depends(get_db)):
    return LeaveInfo.from_leave(svc.create_leave(db, me, _form(body)))


@router.get("/{leave_id}", response_model=LeaveInfo)
def read_leave(leave_id: int, me: User = Depends(student_only), db: Session = Depends(get_db)):
    return LeaveInfo.from_leave(svc.my_leave(db, me, leave_id))


@router.put("/{leave_id}", response_model=LeaveInfo)
def change_leave(leave_id: int, body: LeaveBody, me: User = Depends(student_only),
                 db: Session = Depends(get_db)):
    return LeaveInfo.from_leave(svc.edit_leave(db, me, leave_id, _form(body)))


@router.delete("/{leave_id}", status_code=204)
def drop_leave(leave_id: int, me: User = Depends(student_only), db: Session = Depends(get_db)):
    svc.remove_leave(db, me, leave_id)
    return Response(status_code=204)


@router.post("/{leave_id}/send", response_model=LeaveInfo)
def send(leave_id: int, me: User = Depends(student_only), db: Session = Depends(get_db)):
    return LeaveInfo.from_leave(svc.send_leave(db, me, leave_id))


@router.post("/{leave_id}/withdraw", response_model=LeaveInfo)
def withdraw(leave_id: int, me: User = Depends(student_only), db: Session = Depends(get_db)):
    return LeaveInfo.from_leave(svc.withdraw_leave(db, me, leave_id))
