// 有 data-confirm 的按鈕，按下去先跳確認框
document.addEventListener('click', function (e) {
  var btn = e.target.closest('[data-confirm]');
  if (btn && !confirm(btn.dataset.confirm)) {
    e.preventDefault();
  }
});

// 提示訊息：點 ✕ 關掉，4 秒後自己消失
var notice = document.querySelector('.notice');
if (notice) {
  var closeNotice = function () {
    notice.classList.add('bye');
    setTimeout(function () { notice.remove(); }, 300);
  };
  notice.querySelector('.notice-x').addEventListener('click', closeNotice);
  setTimeout(closeNotice, 4000);
}

// ---------- 登入頁 ----------
var showPw = document.querySelector('[data-show-password]');
if (showPw) {
  var pw = document.getElementById(showPw.dataset.showPassword);
  showPw.addEventListener('change', function () {
    pw.type = showPw.checked ? 'text' : 'password';
  });

  // 偵測大寫鎖定
  var capsTip = document.getElementById('caps-tip');
  pw.addEventListener('keyup', function (e) {
    capsTip.hidden = !(e.getModifierState && e.getModifierState('CapsLock'));
  });
}

document.querySelectorAll('.demo-pick').forEach(function (btn) {
  btn.addEventListener('click', function () {
    document.querySelector('input[name=account]').value = btn.dataset.account;
    document.querySelector('input[name=password]').value = btn.dataset.pw;
    btn.closest('.login-box').querySelector('form').requestSubmit();
  });
});

// ---------- 請假表單 ----------
var leaveForm = document.getElementById('leave-form');
if (leaveForm) {
  var start = leaveForm.querySelector('[name=start_date]');
  var end = leaveForm.querySelector('[name=end_date]');
  var dayTip = document.getElementById('day-count');
  var maxDays = Number(dayTip.dataset.max);

  var countDays = function () {
    end.min = start.value;
    if (!start.value || !end.value) { dayTip.textContent = ''; return; }
    var days = Math.round((new Date(end.value) - new Date(start.value)) / 86400000) + 1;
    if (days < 1) {
      dayTip.textContent = '結束日期比開始日期早';
    } else if (days > maxDays) {
      dayTip.textContent = '共 ' + days + ' 天，超過上限 ' + maxDays + ' 天';
    } else {
      dayTip.textContent = '共 ' + days + ' 天';
    }
    dayTip.classList.toggle('over', days < 1 || days > maxDays);
  };
  // 開始日期改了，結束日期如果比較早就跟著改
  start.addEventListener('change', function () {
    if (end.value < start.value) end.value = start.value;
    countDays();
  });
  end.addEventListener('change', countDays);
  countDays();

  var reason = leaveForm.querySelector('[name=reason]');
  var reasonTip = document.getElementById('reason-count');
  var limit = Number(reasonTip.dataset.limit);
  var countReason = function () {
    reasonTip.textContent = reason.value.length + ' / ' + limit;
    reasonTip.classList.toggle('over', reason.value.length > limit - 20);
  };
  reason.addEventListener('input', countReason);
  countReason();

  // 草稿暫存在瀏覽器，不小心關掉頁面還找得回來（只有新增假單用）
  var draftKey = 'leave-draft';
  if (leaveForm.action.endsWith('/me/leaves/new')) {
    try {
      var saved = localStorage.getItem(draftKey);
      if (saved && !reason.value) {
        reason.value = saved;
        countReason();
      }
      reason.addEventListener('input', function () {
        localStorage.setItem(draftKey, reason.value);
      });
      leaveForm.addEventListener('submit', function () {
        localStorage.removeItem(draftKey);
      });
    } catch (err) { /* 無痕模式可能不能用 localStorage，沒關係 */ }
  }
}

// ---------- 導師審核 ----------
var decision = document.getElementById('decision-form');
if (decision) {
  var comment = decision.querySelector('[name=comment]');

  decision.querySelectorAll('.tag-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      comment.value = comment.value ? comment.value + '，' + btn.textContent : btn.textContent;
      comment.focus();
    });
  });

  // 駁回一定要寫原因
  decision.querySelector('[data-need-comment]').addEventListener('click', function (e) {
    if (!comment.value.trim()) {
      e.preventDefault();
      comment.classList.remove('shake');
      void comment.offsetWidth;
      comment.classList.add('shake');
      comment.placeholder = '駁回時要寫原因喔';
      comment.focus();
    } else if (!confirm('確定駁回這張假單？')) {
      e.preventDefault();
    }
  });
}
