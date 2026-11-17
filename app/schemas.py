from datetime import date, datetime

from pydantic import BaseModel

from .models import LeaveRequest, User


class LoginBody(BaseModel):
    account: str
    password: str


class UserInfo(BaseModel):
    id: int
    account: str
    display_name: str
    role: str
    class_name: str

    @classmethod
    def from_user(cls, u: User):
        return cls(id=u.id, account=u.account, display_name=u.display_name,
                   role=u.role.value, class_name=u.class_name)


class LeaveBody(BaseModel):
    leave_type: str
    start_date: date
    end_date: date
    reason: str


class LeaveInfo(BaseModel):
    id: int
    leave_type: str
    start_date: date
    end_date: date
    days: int
    reason: str
    status: str
    status_text: str
    reply: str
    updated_at: datetime

    @classmethod
    def from_leave(cls, x: LeaveRequest):
        return cls(id=x.id, leave_type=x.leave_type, start_date=x.start_date,
                   end_date=x.end_date, days=x.days, reason=x.reason,
                   status=x.status.value, status_text=x.status.label,
                   reply=x.reply, updated_at=x.updated_at)


class InboxItem(LeaveInfo):
    student: str
    class_name: str

    @classmethod
    def from_pair(cls, x: LeaveRequest, student: User):
        base = LeaveInfo.from_leave(x).model_dump()
        return cls(**base, student=student.display_name, class_name=student.class_name)


class DecisionBody(BaseModel):
    approve: bool
    comment: str = ""
