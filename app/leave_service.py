"""假單的商業邏輯，狀態怎麼變都寫在這裡。

草稿 ──送出──> 待審核 ──核准──> 已核准
  ^              │  └───駁回──> 已駁回 ──修改後重新送出──> 待審核
  └────撤回──────┘
"""
from datetime import date, datetime

from fastapi import HTTPException
from sqlmodel import Session, select

from .models import (LEAVE_TYPES, MAX_DAYS, REASON_LIMIT, LeaveLog, LeaveRequest,
                     LeaveStatus, User)

EDITABLE = (LeaveStatus.DRAFT, LeaveStatus.REJECTED)


class LeaveForm:
    """把表單 / JSON 傳進來的欄位檢查一遍"""

    def __init__(self, leave_type: str, start_date, end_date, reason: str):
        if leave_type not in LEAVE_TYPES:
            raise HTTPException(400, "假別不正確")
        start = _to_date(start_date, "開始日期")
        end = _to_date(end_date, "結束日期")
        if end < start:
            raise HTTPException(400, "結束日期不能早於開始日期")
        if (end - start).days + 1 > MAX_DAYS:
            raise HTTPException(400, f"一次最多請 {MAX_DAYS} 天")
        reason = (reason or "").strip()
        if not reason:
            raise HTTPException(400, "請填寫請假事由")
        if len(reason) > REASON_LIMIT:
            raise HTTPException(400, f"事由最多 {REASON_LIMIT} 字")
        self.leave_type, self.start, self.end, self.reason = leave_type, start, end, reason


def _to_date(value, name: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise HTTPException(400, f"{name}格式不正確")


def _log(db: Session, leave: LeaveRequest, user: User, action: str, note: str = ""):
    db.add(LeaveLog(leave_id=leave.id, actor_id=user.id, action=action, note=note))


def _commit(db: Session, leave: LeaveRequest) -> LeaveRequest:
    leave.updated_at = datetime.now()
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return leave


def logs_of(db: Session, leave_id: int):
    stmt = (select(LeaveLog, User)
            .join(User, LeaveLog.actor_id == User.id)
            .where(LeaveLog.leave_id == leave_id)
            .order_by(LeaveLog.at, LeaveLog.id))
    return db.exec(stmt).all()


# ===== 學生 =====

def my_leaves(db: Session, student: User):
    stmt = (select(LeaveRequest)
            .where(LeaveRequest.student_id == student.id)
            .order_by(LeaveRequest.start_date.desc(), LeaveRequest.id.desc()))
    return db.exec(stmt).all()


def my_leave(db: Session, student: User, leave_id: int) -> LeaveRequest:
    leave = db.get(LeaveRequest, leave_id)
    if leave is None:
        raise HTTPException(404, "找不到這張假單")
    if leave.student_id != student.id:
        raise HTTPException(403, "只能查看自己的假單")
    return leave


def create_leave(db: Session, student: User, form: LeaveForm) -> LeaveRequest:
    leave = LeaveRequest(student_id=student.id, leave_type=form.leave_type,
                         start_date=form.start, end_date=form.end, reason=form.reason)
    db.add(leave)
    db.flush()
    _log(db, leave, student, "建立")
    return _commit(db, leave)


def edit_leave(db: Session, student: User, leave_id: int, form: LeaveForm) -> LeaveRequest:
    leave = my_leave(db, student, leave_id)
    if leave.status not in EDITABLE:
        raise HTTPException(409, f"{leave.status.label}的假單不能修改")
    leave.leave_type = form.leave_type
    leave.start_date, leave.end_date = form.start, form.end
    leave.reason = form.reason
    _log(db, leave, student, "修改")
    return _commit(db, leave)


def remove_leave(db: Session, student: User, leave_id: int):
    leave = my_leave(db, student, leave_id)
    if leave.status != LeaveStatus.DRAFT:
        raise HTTPException(409, "只有草稿可以刪除")
    for log in db.exec(select(LeaveLog).where(LeaveLog.leave_id == leave.id)).all():
        db.delete(log)
    db.delete(leave)
    db.commit()


def send_leave(db: Session, student: User, leave_id: int) -> LeaveRequest:
    leave = my_leave(db, student, leave_id)
    if leave.status not in EDITABLE:
        raise HTTPException(409, "這張假單已經送出了")
    action = "重新送出" if leave.status == LeaveStatus.REJECTED else "送出申請"
    leave.status = LeaveStatus.PENDING
    leave.reply = ""
    _log(db, leave, student, action)
    return _commit(db, leave)


def withdraw_leave(db: Session, student: User, leave_id: int) -> LeaveRequest:
    leave = my_leave(db, student, leave_id)
    if leave.status != LeaveStatus.PENDING:
        raise HTTPException(409, "只有待審核的假單可以撤回")
    leave.status = LeaveStatus.DRAFT
    _log(db, leave, student, "撤回")
    return _commit(db, leave)


def approved_days(leaves) -> int:
    return sum(x.days for x in leaves if x.status == LeaveStatus.APPROVED)


# ===== 導師 =====

def inbox(db: Session, done: bool = False):
    """done=False 是待審核，done=True 是已處理（核准 + 駁回）"""
    if done:
        cond = LeaveRequest.status.in_([LeaveStatus.APPROVED, LeaveStatus.REJECTED])
        order = LeaveRequest.updated_at.desc()
    else:
        cond = LeaveRequest.status == LeaveStatus.PENDING
        order = LeaveRequest.start_date
    stmt = (select(LeaveRequest, User)
            .join(User, LeaveRequest.student_id == User.id)
            .where(cond)
            .order_by(order))
    return db.exec(stmt).all()


def leave_for_teacher(db: Session, leave_id: int):
    leave = db.get(LeaveRequest, leave_id)
    # 草稿是學生自己的，導師看不到
    if leave is None or leave.status == LeaveStatus.DRAFT:
        raise HTTPException(404, "找不到這張假單")
    return leave, db.get(User, leave.student_id)


def decide(db: Session, teacher: User, leave_id: int, approve: bool, comment: str = "") -> LeaveRequest:
    leave, _ = leave_for_teacher(db, leave_id)
    if leave.status != LeaveStatus.PENDING:
        raise HTTPException(409, "這張假單已經處理過了")
    comment = (comment or "").strip()
    if not approve and not comment:
        raise HTTPException(400, "駁回時請說明原因")
    leave.status = LeaveStatus.APPROVED if approve else LeaveStatus.REJECTED
    leave.reply = comment
    _log(db, leave, teacher, "核准" if approve else "駁回", comment)
    return _commit(db, leave)
