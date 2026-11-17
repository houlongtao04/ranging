# 線上請假系統

用 FastAPI 做的學生請假／導師審核網站。學生線上填假單，導師在網站上核准或駁回，每張假單都會留下處理紀錄。

## 功能

**學生**
- 我的假單：卡片清單，依狀態分頁，上方顯示待審核數、已核准天數、被駁回數
- 填寫假單：假別（病假／事假／公假／喪假）、開始與結束日期、請假事由
- 存成草稿，或直接送出申請
- 待審核的假單可以撤回（回到草稿）
- 被駁回的假單可以看到導師的原因，修改後重新送出
- 草稿可以刪除

**導師**
- 待審核／已處理兩個分頁
- 查看假單內容、該學生已核准的天數、處理紀錄
- 核准（意見可不填）或駁回（一定要寫原因），有常用意見可以一鍵帶入

**假單狀態**

```
草稿 ──送出──> 待審核 ──核准──> 已核准
  ^              │
  └────撤回──────┤
                 └──駁回──> 已駁回 ──修改後重新送出──> 待審核
```

**規則**
- 結束日期不能早於開始日期，一張假單最多 14 天
- 事由必填，最多 300 字
- 只有草稿、已駁回可以修改；只有草稿可以刪除
- 學生只能看自己的假單；導師看不到學生的草稿

## 執行方式

需要 Python 3.10 以上。

```bash
python -m venv .venv
.venv\Scripts\activate        # macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

打開 http://127.0.0.1:8000 ，API 文件在 http://127.0.0.1:8000/docs 。

第一次啟動會建立 `leave.db`，並放入測試帳號（密碼都是 `pass1234`）和 12 張範例假單：

| 帳號 | 名稱 | 角色 |
|------|------|------|
| s001 | 林佳穎 | 學生 |
| s002 | 張家豪 | 學生 |
| s003 | 陳怡君 | 學生 |
| s004 | 王冠宇 | 學生 |
| s005 | 李思妤 | 學生 |
| t001 | 黃志明 | 導師 |

範例假單四種狀態都有（待審核 4、已核准 4、已駁回 2、草稿 2），日期以啟動當天往前後推算。登入頁點「測試帳號」可以一鍵登入。

想重置資料就刪掉 `leave.db` 再重新啟動。

## 測試

```bash
python -m pytest
```

## 使用技術

- FastAPI
- SQLModel + SQLite
- Jinja2 樣板 + 原生 JavaScript
- Session cookie 登入，密碼用 scrypt 雜湊
- pytest

## 專案結構

```
app/
  main.py            進入點、錯誤處理
  db.py              資料庫連線、測試帳號與範例假單
  models.py          資料表（User、LeaveRequest、LeaveLog）與狀態
  security.py        密碼雜湊、登入、角色檢查
  leave_service.py   假單的檢查與狀態轉換規則
  schemas.py         API 輸入輸出格式
  api/               JSON API
    auth.py          /api/auth/...
    student.py       /api/leaves/...
    teacher.py       /api/inbox/...
  web/               網頁畫面
    common.py        樣板、提示訊息
    account_views.py 登入、登出、首頁
    student_views.py /me/leaves/...
    teacher_views.py /inbox/...
  templates/         HTML 樣板（student/、teacher/）
  static/            css/、js/
tests/               API 與網頁測試
```

## API

| 方法 | 路徑 | 角色 | 說明 |
|------|------|------|------|
| POST | /api/auth/login | - | 登入 |
| POST | /api/auth/logout | - | 登出 |
| GET | /api/auth/me | 已登入 | 目前使用者 |
| GET | /api/leaves | 學生 | 我的假單 |
| POST | /api/leaves | 學生 | 新增假單（草稿） |
| GET | /api/leaves/{id} | 學生 | 假單內容 |
| PUT | /api/leaves/{id} | 學生 | 修改（限草稿、已駁回） |
| DELETE | /api/leaves/{id} | 學生 | 刪除（限草稿） |
| POST | /api/leaves/{id}/send | 學生 | 送出／重新送出 |
| POST | /api/leaves/{id}/withdraw | 學生 | 撤回（限待審核） |
| GET | /api/inbox?done=false | 導師 | 待審核（done=true 為已處理） |
| GET | /api/inbox/{id} | 導師 | 假單內容 |
| POST | /api/inbox/{id}/decision | 導師 | 審核 `{"approve": true/false, "comment": ""}` |

錯誤代碼：401 未登入、403 角色不符或不是自己的假單、404 找不到、409 目前狀態不能做這個操作、400 欄位錯誤。
