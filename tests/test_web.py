from datetime import date

from sqlmodel import Session, select

from app.db import DEMO_LEAVES, create_demo_leaves
from app.models import LeaveLog, LeaveRequest

TODAY = date.today().isoformat()


def web_login(c, account):
    res = c.post("/login", data={"account": account, "password": "pass1234"},
                 follow_redirects=False)
    assert res.status_code == 303
    return c


def form(**kw):
    data = {"leave_type": "事假", "start_date": TODAY, "end_date": TODAY, "reason": "家裡有事"}
    data.update(kw)
    return data


def test_redirect_when_not_logged_in(login_as):
    res = login_as().get("/me/leaves", follow_redirects=False)
    assert res.status_code == 303 and res.headers["location"] == "/login"


def test_login_error(login_as):
    res = login_as().post("/login", data={"account": "s001", "password": "x"})
    assert res.status_code == 400
    assert "帳號或密碼錯誤" in res.text


def test_home_by_role(login_as):
    s = web_login(login_as(), "s001")
    assert s.get("/", follow_redirects=False).headers["location"] == "/me/leaves"
    t = web_login(login_as(), "t001")
    assert t.get("/", follow_redirects=False).headers["location"] == "/inbox"


def test_whole_flow(login_as):
    s = web_login(login_as(), "s001")
    res = s.post("/me/leaves/new", data=form(reason="回家一趟", then="send"))
    assert "已送出，等導師審核" in res.text
    lid = s.get("/api/leaves").json()[0]["id"]

    t = web_login(login_as(), "t001")
    res = t.get("/inbox")
    assert "林佳穎" in res.text and "回家一趟" in res.text
    res = t.get(f"/inbox/{lid}")
    assert "處理紀錄" in res.text and "送出申請" in res.text

    # 駁回沒寫原因會被擋下
    res = t.post(f"/inbox/{lid}", data={"decision": "reject", "comment": ""})
    assert "駁回時請說明原因" in res.text
    res = t.post(f"/inbox/{lid}", data={"decision": "reject", "comment": "日期寫錯"})
    assert "已駁回這張假單" in res.text

    res = s.get("/me/leaves")
    assert "已駁回" in res.text and "導師：日期寫錯" in res.text
    res = s.get(f"/me/leaves/{lid}/edit")
    assert "日期寫錯" in res.text and "重新送出" in res.text


def test_form_error_keeps_input(login_as):
    s = web_login(login_as(), "s001")
    res = s.post("/me/leaves/new", data=form(end_date="2000-01-01", reason="保留我"))
    assert res.status_code == 400
    assert "結束日期不能早於開始日期" in res.text and "保留我" in res.text


def test_withdraw_and_delete(login_as):
    s = web_login(login_as(), "s001")
    s.post("/me/leaves/new", data=form(then="send"))
    lid = s.get("/api/leaves").json()[0]["id"]

    res = s.post(f"/me/leaves/{lid}/delete")
    assert "只有草稿可以刪除" in res.text
    res = s.post(f"/me/leaves/{lid}/withdraw")
    assert "已撤回" in res.text
    res = s.post(f"/me/leaves/{lid}/delete")
    assert "草稿已刪除" in res.text


def test_student_filter_and_stats(login_as):
    s = web_login(login_as(), "s001")
    s.post("/me/leaves/new", data=form(reason="草稿那張"))
    s.post("/me/leaves/new", data=form(reason="送出那張", then="send"))

    res = s.get("/me/leaves")
    assert "草稿那張" in res.text and "送出那張" in res.text
    res = s.get("/me/leaves?show=pending")
    assert "送出那張" in res.text and "草稿那張" not in res.text
    res = s.get("/me/leaves?show=approved")
    assert "這個分類目前沒有假單" in res.text


def test_wrong_role_page(login_as):
    s = web_login(login_as(), "s001")
    res = s.get("/inbox")
    assert res.status_code == 403 and "只開放給導師" in res.text


def test_demo_data(test_engine):
    with Session(test_engine) as db:
        create_demo_leaves(db)
        rows = db.exec(select(LeaveRequest)).all()
        logs = db.exec(select(LeaveLog)).all()
    assert len(rows) == len(DEMO_LEAVES)
    assert {x.status.value for x in rows} == {"draft", "pending", "approved", "rejected"}
    # 被駁回的一定有原因；重新送出的那張 reply 要是空的
    assert all(x.reply for x in rows if x.status.value == "rejected")
    assert all(not x.reply for x in rows if x.status.value == "pending")
    # 每張假單的紀錄時間要照順序
    for x in rows:
        times = [g.at for g in logs if g.leave_id == x.id]
        assert times == sorted(times) and x.updated_at == times[-1]


def test_demo_data_on_pages(test_engine, login_as):
    with Session(test_engine) as db:
        create_demo_leaves(db)
    t = web_login(login_as(), "t001")
    res = t.get("/inbox")
    assert "待審核 4" in res.text and "王冠宇" in res.text
    s = web_login(login_as(), "s001")
    res = s.get("/me/leaves")
    assert "急性腸胃炎" in res.text
