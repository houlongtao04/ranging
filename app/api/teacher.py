from fastapi import APIRouter, Depends
from sqlmodel import Session

from .. import leave_service as svc
from ..db import get_db
from ..models import User
from ..schemas import DecisionBody, InboxItem, LeaveInfo
from ..security import teacher_only

router = APIRouter(prefix="/api/inbox", tags=["導師"])


@router.get("", response_model=list[InboxItem])
def inbox(done: bool = False, me: User = Depends(teacher_only), db: Session = Depends(get_db)):
    """done=false 待審核；done=true 已處理"""
    return [InboxItem.from_pair(x, s) for x, s in svc.inbox(db, done)]


@router.get("/{leave_id}", response_model=InboxItem)
def inbox_item(leave_id: int, me: User = Depends(teacher_only), db: Session = Depends(get_db)):
    return InboxItem.from_pair(*svc.leave_for_teacher(db, leave_id))


@router.post("/{leave_id}/decision", response_model=LeaveInfo)
def make_decision(leave_id: int, body: DecisionBody, me: User = Depends(teacher_only),
                  db: Session = Depends(get_db)):
    return LeaveInfo.from_leave(svc.decide(db, me, leave_id, body.approve, body.comment))
