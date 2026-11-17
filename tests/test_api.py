from datetime import date, timedelta

TODAY = date.today()


def leave_body(days=1, **kw):
    body = {
        "leave_type": "病假",
        "start_date": TODAY.isoformat(),
        "end_date": (TODAY + timedelta(days=days - 1)).isoformat(),
        "reason": "身體不舒服",
    }
    body.update(kw)
    return body


def make_draft(c, **kw):
    res = c.post("/api/leaves", json=leave_body(**kw))
    assert res.status_code == 201, res.text
    return res.json()


def make_pending(c, **kw):
    x = make_draft(c, **kw)
    res = c.post(f"/api/leaves/{x['id']}/send")
    assert res.status_code == 200
    return res.json()


# ===== 登入、權限 =====

def test_wrong_password(login_as):
    res = login_as().post("/api/auth/login", json={"account": "s001", "password": "nope"})
    assert res.status_code == 401


def test_need_login(login_as):
    c = login_as()
    assert c.get("/api/leaves").status_code == 401
    assert c.get("/api/inbox").status_code == 401


def test_me(stu):
    me = stu.get("/api/auth/me").json()
    assert me["account"] == "s001" and me["role"] == "student"


def test_role_guard(stu, teacher):
    assert stu.get("/api/inbox").status_code == 403
    assert teacher.get("/api/leaves").status_code == 403


def test_logout(stu):
    stu.post("/api/auth/logout")
    assert stu.get("/api/auth/me").status_code == 401


# ===== 學生 =====

def test_new_leave_is_draft(stu):
    x = make_draft(stu, days=3)
    assert x["status"] == "draft"
    assert x["days"] == 3


def test_validation(stu):
    bad = [
        leave_body(leave_type="颱風假"),
        leave_body(start_date="2026-05-10", end_date="2026-05-09"),
        leave_body(days=15),
        leave_body(reason="   "),
        leave_body(reason="字" * 301),
    ]
    for body in bad:
        assert stu.post("/api/leaves", json=body).status_code == 400, body


def test_edit_and_delete_draft(stu):
    x = make_draft(stu)
    res = stu.put(f"/api/leaves/{x['id']}", json=leave_body(days=2, leave_type="事假"))
    assert res.json()["leave_type"] == "事假" and res.json()["days"] == 2
    assert stu.delete(f"/api/leaves/{x['id']}").status_code == 204
    assert stu.get(f"/api/leaves/{x['id']}").status_code == 404


def test_pending_is_locked(stu):
    x = make_pending(stu)
    assert x["status"] == "pending"
    assert stu.put(f"/api/leaves/{x['id']}", json=leave_body()).status_code == 409
    assert stu.delete(f"/api/leaves/{x['id']}").status_code == 409
    assert stu.post(f"/api/leaves/{x['id']}/send").status_code == 409


def test_withdraw(stu):
    x = make_pending(stu)
    res = stu.post(f"/api/leaves/{x['id']}/withdraw")
    assert res.json()["status"] == "draft"
    # 草稿不能再撤回
    assert stu.post(f"/api/leaves/{x['id']}/withdraw").status_code == 409


def test_cannot_touch_others(stu, login_as):
    x = make_draft(stu)
    other = login_as("s002")
    assert other.get(f"/api/leaves/{x['id']}").status_code == 403
    assert other.post(f"/api/leaves/{x['id']}/send").status_code == 403
    assert other.get("/api/leaves").json() == []


# ===== 導師 =====

def test_inbox_only_pending(stu, teacher):
    make_draft(stu, reason="還在寫")
    make_pending(stu, reason="已送出")
    rows = teacher.get("/api/inbox").json()
    assert [r["reason"] for r in rows] == ["已送出"]
    assert rows[0]["student"] == "林佳穎"


def test_teacher_cannot_see_draft(stu, teacher):
    x = make_draft(stu)
    assert teacher.get(f"/api/inbox/{x['id']}").status_code == 404


def test_approve(stu, teacher):
    x = make_pending(stu)
    res = teacher.post(f"/api/inbox/{x['id']}/decision", json={"approve": True})
    assert res.json()["status"] == "approved"
    assert teacher.get("/api/inbox").json() == []
    assert [r["id"] for r in teacher.get("/api/inbox?done=true").json()] == [x["id"]]
    # 核准後學生不能改
    assert stu.put(f"/api/leaves/{x['id']}", json=leave_body()).status_code == 409


def test_reject_needs_comment(stu, teacher):
    x = make_pending(stu)
    res = teacher.post(f"/api/inbox/{x['id']}/decision", json={"approve": False, "comment": " "})
    assert res.status_code == 400


def test_reject_then_resend(stu, teacher):
    x = make_pending(stu)
    res = teacher.post(f"/api/inbox/{x['id']}/decision",
                       json={"approve": False, "comment": "請附證明"})
    assert res.json()["status"] == "rejected"
    assert stu.get(f"/api/leaves/{x['id']}").json()["reply"] == "請附證明"

    # 被駁回可以修改後重新送出，但不能刪
    assert stu.delete(f"/api/leaves/{x['id']}").status_code == 409
    assert stu.put(f"/api/leaves/{x['id']}", json=leave_body(reason="已附證明")).status_code == 200
    res = stu.post(f"/api/leaves/{x['id']}/send")
    assert res.json()["status"] == "pending" and res.json()["reply"] == ""


def test_decide_twice(stu, teacher):
    x = make_pending(stu)
    teacher.post(f"/api/inbox/{x['id']}/decision", json={"approve": True})
    res = teacher.post(f"/api/inbox/{x['id']}/decision", json={"approve": False, "comment": "x"})
    assert res.status_code == 409


def test_decide_not_found(teacher):
    assert teacher.post("/api/inbox/999/decision", json={"approve": True}).status_code == 404
