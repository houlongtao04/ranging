import os
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from .models import LeaveLog, LeaveRequest, LeaveStatus, Role, User

ROOT = Path(__file__).resolve().parent.parent
DB_URL = os.getenv("DB_URL", f"sqlite:///{ROOT / 'leave.db'}")

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

DEMO_PASSWORD = "pass1234"
DEMO_USERS = [
    # 帳號, 名稱, 角色, 班級
    ("s001", "林佳穎", Role.STUDENT, "資工三甲"),
    ("s002", "張家豪", Role.STUDENT, "資工三甲"),
    ("s003", "陳怡君", Role.STUDENT, "資工三甲"),
    ("s004", "王冠宇", Role.STUDENT, "資工三甲"),
    ("s005", "李思妤", Role.STUDENT, "資工三甲"),
    ("t001", "黃志明", Role.TEACHER, "資工三甲"),
]

D, P, A, R = LeaveStatus.DRAFT, LeaveStatus.PENDING, LeaveStatus.APPROVED, LeaveStatus.REJECTED
SEND, OK, NO = ("送出申請", ""), ("核准", ""), ("駁回", "")

# 範例假單：學生, 假別, 開始(距今天幾天), 結束, 事由, 狀態, 幾天前建立, 建立之後的處理過程
DEMO_LEAVES = [
    ("s001", "病假", 1, 2, "感冒發燒，醫生建議在家休息兩天，附上診斷證明。", P, 0, [SEND]),
    ("s001", "事假", 10, 10, "家裡有事需要回南部一趟。", D, 1, []),
    ("s001", "病假", -20, -19, "急性腸胃炎，在家休養。", A, 22,
     [SEND, ("核准", "好好休息，早日康復")]),
    ("s002", "公假", -7, -7, "代表系上參加全國大專程式競賽。", A, 10,
     [SEND, ("核准", "比賽加油！")]),
    ("s002", "事假", 3, 3, "當天上午要考機車駕照路考。", P, 1, [SEND]),
    ("s003", "喪假", -5, -3, "外婆過世，回花蓮奔喪。", A, 6,
     [SEND, ("核准", "節哀順變，課業有需要再跟我說")]),
    ("s003", "事假", -12, -12, "前一天熬夜做報告，早上起不來。", R, 12,
     [SEND, ("駁回", "這不是請假的理由，請準時上課")]),
    ("s004", "病假", 0, 0, "牙齒痛要去看牙醫，已附上看診證明。", P, 3,
     [SEND, ("駁回", "請附看診證明"), ("修改", ""), ("重新送出", "")]),
    ("s004", "公假", 5, 6, "系學會帶隊參加新生宿營。", P, 2, [SEND]),
    ("s005", "事假", -2, -2, "去高雄看演唱會。", R, 4,
     [SEND, ("駁回", "期中考週不建議請事假")]),
    ("s005", "病假", -30, -28, "流感（A 型），附診斷書。", A, 31, [SEND, OK]),
    ("s005", "事假", 14, 15, "姊姊結婚，要回家幫忙。", D, 0, []),
]


def get_db():
    with Session(engine) as db:
        yield db


def create_demo_users(db: Session) -> bool:
    """資料庫沒有任何使用者時才建立，回傳有沒有建立"""
    from .security import make_hash

    if db.exec(select(User)).first() is not None:
        return False
    for account, name, role, class_name in DEMO_USERS:
        db.add(User(account=account, display_name=name, role=role, class_name=class_name,
                    pw_hash=make_hash(DEMO_PASSWORD)))
    db.commit()
    return True


# 範例紀錄每一步之間隔多久（都落在白天）
GAPS = [timedelta(hours=1, minutes=17), timedelta(hours=3, minutes=30),
        timedelta(hours=2, minutes=5), timedelta(hours=1, minutes=40)]


def create_demo_leaves(db: Session):
    users = {u.account: u for u in db.exec(select(User)).all()}
    teacher = users["t001"]
    today = date.today()
    now = datetime.now().replace(second=0, microsecond=0)

    for account, kind, start, end, reason, status, ago, steps in DEMO_LEAVES:
        student = users[account]
        # 建立時間往前推，之後每個步驟隔幾個小時，時間軸看起來比較真實
        t = min(now - timedelta(days=ago, hours=3), now.replace(hour=8, minute=30) - timedelta(days=ago))
        leave = LeaveRequest(student_id=student.id, leave_type=kind,
                             start_date=today + timedelta(days=start),
                             end_date=today + timedelta(days=end),
                             reason=reason, status=status, created_at=t)
        db.add(leave)
        db.flush()
        logs = [LeaveLog(leave_id=leave.id, actor_id=student.id, action="建立", at=t)]
        for i, (action, note) in enumerate(steps):
            t = min(t + GAPS[i % len(GAPS)], now)
            actor = teacher if action in ("核准", "駁回") else student
            logs.append(LeaveLog(leave_id=leave.id, actor_id=actor.id, action=action,
                                 note=note, at=t))
        if status in (LeaveStatus.APPROVED, LeaveStatus.REJECTED):
            leave.reply = logs[-1].note
        leave.updated_at = t
        db.add_all(logs)
    db.commit()


def init_db():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        if create_demo_users(db):
            create_demo_leaves(db)
