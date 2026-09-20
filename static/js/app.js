// 全局交互：侧边栏分组折叠、配色主题切换、多赛事倒计时、待办清单
document.addEventListener('DOMContentLoaded', function () {
  // 侧边栏分组折叠
  document.querySelectorAll('.nav-group-toggle').forEach(function (btn) {
    btn.addEventListener('click', function () {
      btn.closest('.nav-group').classList.toggle('collapsed');
    });
  });

  // 侧边栏收缩（仅图标模式，状态存 localStorage）
  var collapseBtn = document.getElementById('sidebar-collapse-btn');
  if (collapseBtn) {
    document.querySelector('.sidebar').classList.toggle('collapsed', localStorage.getItem('sidebar_collapsed') === '1');
    collapseBtn.addEventListener('click', function () {
      var sb = document.querySelector('.sidebar');
      sb.classList.toggle('collapsed');
      localStorage.setItem('sidebar_collapsed', sb.classList.contains('collapsed') ? '1' : '0');
    });
  }
  // 为导航项设置 tooltip 标签（收缩态 hover 提示）
  document.querySelectorAll('.nav-item').forEach(function (item) {
    var label = item.textContent.replace(/进入|开发中/g, '').trim();
    if (label) item.setAttribute('data-label', label);
  });

  // 配色主题（支持多处下拉，顶部栏与设置页共用）
  var saved = localStorage.getItem('theme') || 'theme-beige';
  document.body.classList.add(saved);
  document.querySelectorAll('.theme-select').forEach(function (sel) {
    sel.value = saved;
    sel.addEventListener('change', function () {
      document.body.className = this.value;
      localStorage.setItem('theme', this.value);
      document.querySelectorAll('.theme-select').forEach(function (s) { s.value = this.value; });
    });
  });

  // 多赛事倒计时
  var el = document.getElementById('match-events');
  if (el) initMatchEvents(el);

  // 待办清单
  var todoEl = document.getElementById('todo-list');
  if (todoEl) initTodoList(todoEl);
});

// ---- 通用弹窗 ----
var _appModal = null;
function appModal() {
  if (!_appModal) {
    var mask = document.createElement('div');
    mask.className = 'modal-mask';
    mask.innerHTML = '<div class="modal-box"></div>';
    document.body.appendChild(mask);
    _appModal = mask;
  }
  return _appModal;
}
function appCloseModal() { appModal().style.display = 'none'; }

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
    return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
  });
}

// ---- 多赛事倒计时（按账号隔离，存 localStorage）----
function initMatchEvents(el) {
  var username = document.body.getAttribute('data-username') || 'anonymous';
  var KEY = 'match_events_' + username;
  var card = el.closest ? el.closest('.card') : null;
  var headBtn = card ? card.querySelector('.js-head-add-event') : null;

  function pad(n) { n = String(n); return n.length < 2 ? '0' + n : n; }
  function format(ms) {
    var s = Math.max(0, Math.floor(ms / 1000));
    var d = Math.floor(s / 86400);
    var h = Math.floor((s % 86400) / 3600);
    var m = Math.floor((s % 3600) / 60);
    var ss = s % 60;
    return d + '天 ' + pad(h) + '时 ' + pad(m) + '分 ' + pad(ss) + '秒';
  }
  function fillTime(timeEl, datetime) {
    var remaining = new Date(datetime).getTime() - Date.now();
    if (remaining <= 0) {
      timeEl.textContent = '赛事已结束';
      timeEl.className = 'match-time ended';
    } else {
      timeEl.textContent = format(remaining);
      timeEl.className = 'match-time';
    }
  }
  function load() {
    var raw = localStorage.getItem(KEY);
    if (raw) {
      try { var a = JSON.parse(raw); if (Array.isArray(a)) return a; } catch (e) {}
    }
    return [];
  }
  function save(events) { localStorage.setItem(KEY, JSON.stringify(events)); }

  function render() {
    var events = load();
    if (headBtn) headBtn.style.display = events.length === 0 ? 'none' : 'inline-flex';
    if (events.length === 0) {
      el.innerHTML = '<div class="match-empty"><button class="btn-add-event js-add-event">＋ 添加新事件</button></div>';
      el.querySelector('.js-add-event').addEventListener('click', openAdd);
      return;
    }
    var html = '<div class="match-list">';
    events.forEach(function (ev, i) {
      html += '<div class="match-item" data-id="' + ev.id + '" data-datetime="' + esc(ev.datetime) + '">' +
        '<span class="todo-index">' + (i + 1) + '.</span>' +
        '<div class="match-name">' + esc(ev.name) + '</div>' +
        '<div class="match-time"></div>' +
        '<button class="btn btn-danger btn-sm js-del-event">删除</button>' +
        '</div>';
    });
    html += '</div>';
    el.innerHTML = html;
    el.querySelectorAll('.match-item').forEach(function (item) {
      fillTime(item.querySelector('.match-time'), item.getAttribute('data-datetime'));
    });
    el.querySelectorAll('.js-del-event').forEach(function (btn) {
      btn.addEventListener('click', function () {
        deleteEvent(btn.closest('.match-item').getAttribute('data-id'));
      });
    });
  }

  function deleteEvent(id) {
    var events = load().filter(function (e) { return String(e.id) !== String(id); });
    save(events);
    render();
  }

  function openAdd() {
    var box = appModal().querySelector('.modal-box');
    box.innerHTML =
      '<h3>添加新事件</h3>' +
      '<label>赛事名称<input type="text" id="ev-name" placeholder="如：校篮球决赛"></label>' +
      '<label>比赛日期时间<input type="datetime-local" id="ev-datetime"></label>' +
      '<div class="modal-actions"><button class="btn" id="ev-cancel">取消</button><button class="btn btn-primary" id="ev-ok">确认添加</button></div>';
    appModal().style.display = 'flex';
    document.getElementById('ev-cancel').onclick = appCloseModal;
    document.getElementById('ev-ok').onclick = function () {
      var name = document.getElementById('ev-name').value.trim();
      var datetime = document.getElementById('ev-datetime').value;
      if (!name) { alert('请填写赛事名称'); return; }
      if (!datetime) { alert('请选择比赛日期时间'); return; }
      var events = load();
      events.push({ id: Date.now(), name: name, datetime: datetime });
      save(events);
      appCloseModal();
      render();
    };
  }

  // 每秒自动刷新所有赛事倒计时
  setInterval(function () {
    el.querySelectorAll('.match-item').forEach(function (item) {
      fillTime(item.querySelector('.match-time'), item.getAttribute('data-datetime'));
    });
  }, 1000);

  if (headBtn) headBtn.addEventListener('click', openAdd);
  render();
}

// ---- 待办清单（按账号隔离，存 localStorage）----
function initTodoList(el) {
  var username = document.body.getAttribute('data-username') || 'anonymous';
  var KEY = 'todo_list_' + username;
  var card = el.closest ? el.closest('.card') : null;
  var headBtn = card ? card.querySelector('.js-head-add-todo') : null;

  function load() {
    var raw = localStorage.getItem(KEY);
    if (raw) {
      try { var a = JSON.parse(raw); if (Array.isArray(a)) return a; } catch (e) {}
    }
    return [];
  }
  function save(todos) { localStorage.setItem(KEY, JSON.stringify(todos)); }

  function render() {
    var todos = load();
    if (headBtn) headBtn.style.display = todos.length === 0 ? 'none' : 'inline-flex';
    if (todos.length === 0) {
      el.innerHTML = '<div class="todo-empty"><button class="btn-add-event js-add-todo">＋ 添加待办</button></div>';
      el.querySelector('.js-add-todo').addEventListener('click', openAdd);
      return;
    }
    var html = '<div class="todo-list">';
    todos.forEach(function (t, i) {
      html += '<div class="todo-item" data-id="' + t.id + '">' +
        '<span class="todo-index">' + (i + 1) + '.</span>' +
        '<span class="todo-check' + (t.done ? ' done' : '') + ' js-toggle-todo"></span>' +
        '<span class="todo-title' + (t.done ? ' done' : '') + '">' + esc(t.title) + '</span>' +
        '<button class="btn btn-danger btn-sm js-del-todo">删除</button>' +
        '</div>';
    });
    html += '</div>';
    el.innerHTML = html;
    el.querySelectorAll('.js-toggle-todo').forEach(function (chk) {
      chk.addEventListener('click', function () {
        toggleTodo(chk.closest('.todo-item').getAttribute('data-id'));
      });
    });
    el.querySelectorAll('.js-del-todo').forEach(function (btn) {
      btn.addEventListener('click', function () {
        deleteTodo(btn.closest('.todo-item').getAttribute('data-id'));
      });
    });
  }

  function toggleTodo(id) {
    var todos = load();
    todos.forEach(function (t) { if (String(t.id) === String(id)) t.done = !t.done; });
    save(todos);
    render();
  }
  function deleteTodo(id) {
    var todos = load().filter(function (t) { return String(t.id) !== String(id); });
    save(todos);
    render();
  }

  function openAdd() {
    var box = appModal().querySelector('.modal-box');
    box.innerHTML =
      '<h3>添加待办</h3>' +
      '<label>待办事项<input type="text" id="td-title" placeholder="如：明天写课题"></label>' +
      '<div class="modal-actions"><button class="btn" id="td-cancel">取消</button><button class="btn btn-primary" id="td-ok">确认添加</button></div>';
    appModal().style.display = 'flex';
    document.getElementById('td-cancel').onclick = appCloseModal;
    document.getElementById('td-ok').onclick = function () {
      var title = document.getElementById('td-title').value.trim();
      if (!title) { alert('请填写待办事项'); return; }
      var todos = load();
      todos.push({ id: Date.now(), title: title, done: false });
      save(todos);
      appCloseModal();
      render();
    };
  }

  if (headBtn) headBtn.addEventListener('click', openAdd);
  render();
}

document.addEventListener('click', function (e) {
  if (_appModal && e.target === _appModal) appCloseModal();
});
