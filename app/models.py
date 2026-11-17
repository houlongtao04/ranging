from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

LEAVE_TYPES = ["病假", "事假", "公假", "喪假"]
MAX_DAYS = 14          # 一張假單最多請幾天
REASON_LIMIT = 300     # 事由字數上限


class Role(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"

    @property
    def label(self):
        return {"student": "學生", "teacher": "導師"}[self.value]


class LeaveStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    @property
    def label(self):
        return {
            "draft": "草稿",
            "pending": "待審核",
            "approved": "已核准",
            "rejected": "已駁回",
        }[self.value]


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    account: str = Field(unique=True, index=True)
    display_name: str
    pw_hash: str
    role: Role
    class_name: str = ""


class LeaveRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="user.id", index=True)
    leave_type: str
    start_date: date
    end_date: date
    reason: str
    status: LeaveStatus = Field(default=LeaveStatus.DRAFT)
    reply: str = ""     # 導師的意見
    created_at: datetime = Field(default_factory=datetime.now, sa_type=DateTime)
    updated_at: datetime = Field(default_factory=datetime.now, sa_type=DateTime)

    @property
    def days(self) -> int:
        return (self.end_date - self.start_date).days + 1


class LeaveLog(SQLModel, table=True):
    """假單的處理紀錄，每次狀態改變記一筆"""
    id: Optional[int] = Field(default=None, primary_key=True)
    leave_id: int = Field(foreign_key="leaverequest.id", index=True)
    actor_id: int = Field(foreign_key="user.id")
    action: str
    note: str = ""
    at: datetime = Field(default_factory=datetime.now, sa_type=DateTime)
