// 共享 AI 模块：模型状态 + 会话上下文 + 流式对话（悬浮抽屉与 AI 备课中心共用，状态完全同步）
window.AI = (function () {
  var STATE_KEY = 'ai_model_state';
  var CONV_KEY = 'ai_conversation';

  function getState() {
    var raw = localStorage.getItem(STATE_KEY);
    if (raw) { try { var s = JSON.parse(raw); if (s && s.provider && s.model) return s; } catch (e) {} }
    return { provider: 'deepseek', model: 'deepseek-chat' };
  }
  function setState(provider, model) {
    localStorage.setItem(STATE_KEY, JSON.stringify({ provider: provider, model: model }));
  }
  function getConversation() {
    var raw = localStorage.getItem(CONV_KEY);
    if (raw) { try { var a = JSON.parse(raw); if (Array.isArray(a)) return a; } catch (e) {} }
    return [];
  }
  function setConversation(msgs) {
    localStorage.setItem(CONV_KEY, JSON.stringify(msgs));
  }
  function clearConversation() {
    localStorage.removeItem(CONV_KEY);
  }

  // 初始化服务商/模型下拉，并读取全局状态（两处下拉自动同步）
  function initModelSelectors(providerSel, modelSel, providers) {
    function populateProviders() {
      providerSel.innerHTML = '';
      Object.keys(providers).forEach(function (pid) {
        var opt = document.createElement('option');
        opt.value = pid;
        opt.textContent = providers[pid].name;
        providerSel.appendChild(opt);
      });
    }
    function populateModels(pid) {
      modelSel.innerHTML = '';
      (providers[pid] ? providers[pid].models : []).forEach(function (m) {
        var opt = document.createElement('option');
        opt.value = m.id;
        opt.textContent = m.label + (m.pricing ? '（' + m.pricing + '）' : '');
        modelSel.appendChild(opt);
      });
    }
    var st = getState();
    populateProviders();
    providerSel.value = st.provider;
    populateModels(st.provider);
    modelSel.value = st.model;
    providerSel.addEventListener('change', function () {
      populateModels(this.value);
      setState(this.value, modelSel.value);
    });
    modelSel.addEventListener('change', function () {
      setState(providerSel.value, this.value);
    });
  }

  // 发送用户消息，流式回调 onDelta(delta, full)，返回 Promise<完整回答>
  function send(userText, onDelta) {
    var state = getState();
    var conv = getConversation();
    conv.push({ role: 'user', content: userText });
    setConversation(conv);

    return fetch('/api/ai/chat-stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: state.provider, model: state.model, messages: conv, stream: true })
    }).then(function (resp) {
      if (!resp.ok) return Promise.reject(new Error('请求失败（' + resp.status + '）'));
      var reader = resp.body.getReader();
      var decoder = new TextDecoder();
      var buf = '', full = '';
      function pump() {
        return reader.read().then(function (r) {
          if (r.done) return full;
          buf += decoder.decode(r.value, { stream: true });
          var lines = buf.split('\n');
          buf = lines.pop();
          lines.forEach(function (line) {
            line = line.trim();
            if (line.indexOf('data: ') !== 0) return;
            var payload = line.slice(6);
            if (payload === '[DONE]') return;
            try {
              var obj = JSON.parse(payload);
              if (obj.delta) { full += obj.delta; if (onDelta) onDelta(obj.delta, full); }
              if (obj.error) { full = '⚠️ ' + obj.error; if (onDelta) onDelta('', full); }
            } catch (e) {}
          });
          return pump();
        });
      }
      return pump();
    }).then(function (full) {
      conv.push({ role: 'assistant', content: full });
      setConversation(conv);
      return full;
    });
  }

  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
    });
  }

  return {
    getState: getState, setState: setState,
    getConversation: getConversation, setConversation: setConversation, clearConversation: clearConversation,
    initModelSelectors: initModelSelectors, send: send, escapeHtml: escapeHtml
  };
})();
