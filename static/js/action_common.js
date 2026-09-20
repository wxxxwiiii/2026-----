/* AI 动作识别公共组件：单人诊断弹窗（renderActionModal）+ 骨骼绘制 + 打开弹窗。
   依赖 base.html 底部的 app.js（appModal / appCloseModal / esc）。 */

// MediaPipe Pose 关键点连接（骨骼连线）
var POSE_BONES = [[11,12],[12,24],[24,23],[23,11],[11,13],[13,15],[15,17],[12,14],[14,16],[16,18],[23,25],[25,27],[27,29],[24,26],[26,28],[28,30]];

function drawSkeleton(canvas, landmarks) {
  if (!canvas) return;
  var W = canvas.clientWidth || canvas.width;
  var H = canvas.clientHeight || canvas.height;
  canvas.width = W; canvas.height = H;
  var ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, W, H);
  if (!landmarks || !landmarks.length) return;
  var pts = landmarks.map(function (p) { return { x: p.x * W, y: p.y * H, v: p.v }; });
  ctx.strokeStyle = '#00e676'; ctx.lineWidth = 2;
  POSE_BONES.forEach(function (b) {
    var a = pts[b[0]], c = pts[b[1]];
    if (a && c && a.v > 0.5 && c.v > 0.5) {
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(c.x, c.y); ctx.stroke();
    }
  });
  ctx.fillStyle = '#ff5252';
  pts.forEach(function (p) {
    if (p.v > 0.5) { ctx.beginPath(); ctx.arc(p.x, p.y, 3, 0, Math.PI * 2); ctx.fill(); }
  });
}

/* 渲染单人诊断弹窗。d: {id, student, sport_type, technique_action, video_path,
   result, metrics, landmarks, status, error, created_at} */
function renderActionModal(d) {
  var box = appModal().querySelector('.modal-box');
  box.style.width = '920px';
  box.style.maxHeight = '90vh';
  box.style.overflow = 'auto';
  var title = (d.student || '未指定学生') + ' · ' + (d.sport_type || '') +
    (d.technique_action ? (' · ' + d.technique_action) : '');
  var html = '<h3>' + esc(title) + '</h3><div style="display:flex;gap:16px;flex-wrap:wrap">';
  // 左侧：视频 + 骨骼
  html += '<div style="flex:1;min-width:320px">';
  if (d.video_path) {
    html += '<div style="position:relative">' +
      '<video controls style="width:100%;max-height:320px" src="' + esc(d.video_path) + '"></video>' +
      '<canvas id="pose-canvas" style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none"></canvas>' +
      '</div>';
  } else {
    html += '<p class="muted">暂无视频。</p>';
  }
  html += '</div>';
  // 右侧：文字诊断 + 关节参数
  html += '<div style="flex:1;min-width:320px">';
  html += '<div style="white-space:pre-wrap;margin-bottom:10px;font-size:14px;max-height:180px;overflow:auto">' +
    (d.result ? esc(d.result) : '暂无诊断结果') + '</div>';
  if (d.metrics && Object.keys(d.metrics).length) {
    html += '<table style="font-size:12px"><thead><tr><th>关节</th><th>平均角度</th><th>标准</th><th>偏差</th><th>力矩</th></tr></thead><tbody>';
    for (var j in d.metrics) {
      var m = d.metrics[j];
      html += '<tr><td>' + esc(j) + '</td><td>' + m.avg_angle + '°</td><td>' + m.std_angle + '°</td><td>' + m.dev + '°</td><td>' + m.avg_torque + '</td></tr>';
    }
    html += '</tbody></table>';
  } else if (d.status === 'not_install' || d.status === 'no_human' || d.status === 'failed') {
    html += '<p class="muted">' + esc(d.error || '暂无关节参数') + '</p>';
  } else {
    html += '<p class="muted">暂无关节参数。</p>';
  }
  html += '</div></div>';
  html += '<div class="modal-actions"><button class="btn btn-primary" onclick="appCloseModal()">关闭</button></div>';
  box.innerHTML = html;
  appModal().style.display = 'flex';
  if (d.video_path && d.landmarks && d.landmarks.length) {
    setTimeout(function () { drawSkeleton(document.getElementById('pose-canvas'), d.landmarks); }, 200);
  }
}

/* 通过分析记录 id 打开单人诊断弹窗（按需拉取详情）。 */
function openAnalysisModal(aid) {
  fetch('/action/' + aid + '/detail')
    .then(function (r) { return r.json(); })
    .then(function (d) { renderActionModal(d); })
    .catch(function (e) { alert('加载诊断详情失败：' + e); });
}
