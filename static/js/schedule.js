// 课表组件（前端本地模拟）：首页与教师工作台共用
// 数据按【账号 + 周数】隔离存储在 localStorage，默认全空白，仅显示「+」
(function () {
  var WEEK_KEY = 'schedule_week';
  var BREAK_WEEKS = [17, 18];        // 停课周（上课周为 1-16 周）
  var DAYS = ['周一', '周二', '周三', '周四', '周五'];

  var PERIODS = [
    {no: 1, start: '08:00', end: '08:40'},
    {no: 2, start: '08:50', end: '09:30'},
    {no: 3, start: '09:40', end: '10:20'},
    {no: 4, start: '10:40', end: '11:20'},
    {no: 5, start: '11:30', end: '12:10'},
    {no: 6, start: '14:00', end: '14:40'},
    {no: 7, start: '14:50', end: '15:30'},
    {no: 8, start: '15:50', end: '16:30'},
    {no: 9, start: '16:40', end: '17:20'},
    {no: 10, start: '18:40', end: '19:20'},
    {no: 11, start: '19:30', end: '20:10'}
  ];

  // 分隔行：在第 N 节之后插入
  var BREAKS = [
    {after: 3, label: '大课间', time: '10:20-10:40'},
    {after: 5, label: '午休', time: '12:10-14:00'},
    {after: 7, label: '大课间', time: '15:30-15:50'},
    {after: 9, label: '晚休', time: '17:20-18:40'}
  ];

  function getUsername() {
    var u = document.body ? document.body.getAttribute('data-username') : null;
    return u || 'anonymous';
  }
  function weekDataKey(username, week) {
    return 'schedule_' + username + '_week_' + week;
  }

  function getWeek() {
    var w = parseInt(localStorage.getItem(WEEK_KEY), 10);
    if (!(w >= 1 && w <= 18)) w = 1;
    return w;
  }
  function setWeek(w) { localStorage.setItem(WEEK_KEY, String(w)); }

  function isBreakWeek(w) { return BREAK_WEEKS.indexOf(w) >= 0; }

  function loadWeekData(username, week) {
    var raw = localStorage.getItem(weekDataKey(username, week));
    if (raw) {
      try { var d = JSON.parse(raw); if (d) return d; } catch (e) {}
    }
    return {};
  }
  function saveWeekData(username, week, courses) {
    localStorage.setItem(weekDataKey(username, week), JSON.stringify(courses));
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
    });
  }

  function renderAll() {
    document.querySelectorAll('.schedule-widget').forEach(function (w) { renderOne(w); });
    var sel = document.getElementById('week-select');
    if (sel) sel.value = String(getWeek());
  }

  function renderOne(widget) {
    var username = getUsername();
    var week = getWeek();
    var breakWeek = isBreakWeek(week);
    var courses = breakWeek ? {} : loadWeekData(username, week);
    var size = widget.getAttribute('data-size') || 'large';

    var html = '<table class="schedule-table' + (size === 'small' ? ' sc-small' : '') + '">';
    html += '<thead><tr><th class="sc-time-col">节次</th>';
    for (var d = 0; d < 5; d++) html += '<th>' + DAYS[d] + '</th>';
    html += '</tr></thead><tbody>';

    for (var i = 0; i < PERIODS.length; i++) {
      var p = PERIODS[i];
      html += '<tr>';
      html += '<td class="sc-period"><span class="sc-no">第' + p.no + '节</span><span class="sc-time">' + p.start + '-' + p.end + '</span></td>';
      for (var dd = 0; dd < 5; dd++) {
        var key = dd + '-' + p.no;
        var course = courses[key];
        var cls = 'sc-cell';
        var content;
        if (breakWeek) {
          cls += ' sc-break';
          content = '本周停课';
        } else if (course) {
          cls += ' sc-course';
          content = '<div class="sc-course-name">' + esc(course.name) + '</div>' +
                    '<div class="sc-course-loc">' + esc(course.location || '') + '</div>' +
                    '<div class="sc-course-loc">' + esc(course.cls || '') + '</div>';
        } else {
          cls += ' sc-empty';
          content = '<span class="sc-plus">＋</span>';
        }
        html += '<td class="' + cls + '" data-day="' + dd + '" data-period="' + p.no + '">' + content + '</td>';
      }
      html += '</tr>';
      for (var b = 0; b < BREAKS.length; b++) {
        if (BREAKS[b].after === p.no) {
          html += '<tr class="big-break"><td colspan="6">' + BREAKS[b].label + ' ' + BREAKS[b].time + '</td></tr>';
        }
      }
    }
    html += '</tbody></table>';
    widget.innerHTML = html;
    bindClicks(widget, username, week, breakWeek, courses);
  }

  function bindClicks(widget, username, week, breakWeek, courses) {
    widget.querySelectorAll('.sc-cell').forEach(function (cell) {
      cell.addEventListener('click', function () {
        if (breakWeek) return;
        var day = parseInt(cell.getAttribute('data-day'), 10);
        var period = parseInt(cell.getAttribute('data-period'), 10);
        var key = day + '-' + period;
        var course = courses[key];
        if (course) {
          openActionModal(course, function () {
            delete courses[key];
            saveWeekData(username, week, courses);
            renderAll();
          });
        } else {
          openAddModal(function (name, location, cls) {
            courses[key] = {name: name, location: location, cls: cls};
            saveWeekData(username, week, courses);
            renderAll();
          });
        }
      });
    });
  }

  // ---- 弹窗 ----
  var modal = null;
  function getModal() {
    if (!modal) {
      var mask = document.createElement('div');
      mask.className = 'modal-mask';
      mask.innerHTML = '<div class="modal-box"></div>';
      document.body.appendChild(mask);
      modal = mask;
    }
    return modal;
  }
  function closeModal() { getModal().style.display = 'none'; }

  function openAddModal(onOk) {
    var box = getModal().querySelector('.modal-box');
    box.innerHTML =
      '<h3>添加课程</h3>' +
      '<label>课程名称<input type="text" id="sc-name" placeholder="如：篮球"></label>' +
      '<label>授课地点<input type="text" id="sc-loc" placeholder="如：篮球场"></label>' +
      '<label>学生班级<input type="text" id="sc-cls" placeholder="如：2024级体育1班"></label>' +
      '<div class="modal-actions"><button class="btn" id="sc-cancel">取消</button><button class="btn btn-primary" id="sc-ok">保存</button></div>';
    getModal().style.display = 'flex';
    document.getElementById('sc-cancel').onclick = closeModal;
    document.getElementById('sc-ok').onclick = function () {
      var name = document.getElementById('sc-name').value.trim();
      var loc = document.getElementById('sc-loc').value.trim();
      var cls = document.getElementById('sc-cls').value.trim();
      if (!name) { alert('请填写课程名称'); return; }
      closeModal();
      onOk(name, loc, cls);
    };
  }

  function openActionModal(course, onDelete) {
    var box = getModal().querySelector('.modal-box');
    box.innerHTML =
      '<h3>课程操作</h3>' +
      '<p class="muted">' + esc(course.name) +
        (course.location ? '（' + esc(course.location) + '）' : '') +
        (course.cls ? ' · ' + esc(course.cls) : '') + '</p>' +
      '<div class="modal-actions"><button class="btn" id="sc-cancel">取消</button><button class="btn btn-danger" id="sc-del">删除课程</button></div>';
    getModal().style.display = 'flex';
    document.getElementById('sc-cancel').onclick = closeModal;
    document.getElementById('sc-del').onclick = function () { closeModal(); onDelete(); };
  }

  document.addEventListener('DOMContentLoaded', function () {
    renderAll();
    var sel = document.getElementById('week-select');
    if (sel) {
      sel.value = String(getWeek());
      sel.addEventListener('change', function () {
        setWeek(parseInt(this.value, 10));
        renderAll();
      });
    }
  });

  document.addEventListener('click', function (e) {
    if (modal && e.target === modal) closeModal();
  });
})();
