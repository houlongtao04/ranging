from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlmodel import Session

from .. import leave_service as svc
from ..db import get_db
from ..models import LeaveStatus, User
from ..security import teacher_only
from .common import page, redirect

router = APIRouter(prefix="/inbox", include_in_schema=False)


@router.get("")
def inbox(request: Request, tab: str = "todo", me: User = Depends(teacher_only),
          db: Session = Depends(get_db)):
    todo = svc.inbox(db, done=False)
    done = svc.inbox(db, done=True)
    tab = "done" if tab == "done" else "todo"
    return page(request, "teacher/inbox.html", me=me, tab=tab,
                rows=done if tab == "done" else todo,
                todo_count=len(todo), done_count=len(done))


@router.get("/{leave_id}")
def review(request: Request, leave_id: int, me: User = Depends(teacher_only),
           db: Session = Depends(get_db)):
    leave, student = svc.leave_for_teacher(db, leave_id)
    history = [x for x, _ in svc.inbox(db, done=True) if x.student_id == student.id]
    return page(request, "teacher/review.html", me=me, leave=leave, student=student,
                logs=svc.logs_of(db, leave.id),
                student_days=svc.approved_days(history))


@router.post("/{leave_id}")
def review_submit(request: Request, leave_id: int, decision: str = Form(""),
                  comment: str = Form(""), me: User = Depends(teacher_only),
                  db: Session = Depends(get_db)):
    if decision not in ("approve", "reject"):
        raise HTTPException(400, "請選擇核准或駁回")
    try:
        leave = svc.decide(db, me, leave_id, decision == "approve", comment)
    except HTTPException as e:
        if e.status_code not in (400, 409):
            raise
        return redirect(request, f"/inbox/{leave_id}", e.detail, "warn")
    word = "核准" if leave.status == LeaveStatus.APPROVED else "駁回"
    return redirect(request, "/inbox", f"已{word}這張假單")
