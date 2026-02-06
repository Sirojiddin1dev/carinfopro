/* global window */
(function () {
  function nowTime() {
    var d = new Date();
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function renderMessage(container, msg) {
    var el = document.createElement('div');
    el.className = 'msg' + (msg.sender === 'visitor' ? ' me' : '');
    el.innerHTML = '<div>' + msg.text + '</div><span class="time">' + msg.time + '</span>';
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
  }

  function requestJson(method, url, body) {
    var opts = { method: method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    return fetch(url, opts).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) {
          var err = data && data.detail ? data.detail : 'Request failed';
          throw new Error(err);
        }
        return data;
      });
    });
  }

  function initChat(opts) {
    var userId = opts.userId || 'unknown';
    var restBase = opts.restBase || '';
    var wsBase = opts.wsBase || ((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host);
    var userEl = document.getElementById('userId');
    var list = document.getElementById('messages');
    var input = document.getElementById('messageInput');
    var btn = document.getElementById('sendBtn');
    var statusEl = document.getElementById('status');
    var retryBtn = document.getElementById('retryBtn');
    var ws = null;
    var roomId = null;
    var visitorToken = null;

    if (userEl) userEl.textContent = userId;

    function setStatus(text, kind) {
      statusEl.textContent = text;
      statusEl.className = 'status' + (kind ? ' ' + kind : '');
    }

    function connectWebSocket(wsPath) {
      var paths = [wsPath, '/back' + wsPath];
      var index = 0;
      var opened = false;

      function tryConnect() {
        var path = paths[index];
        var url = wsBase + path + '?visitor=' + encodeURIComponent(visitorToken);
        ws = new WebSocket(url);

        ws.onopen = function () {
          opened = true;
          setStatus('Ulandi', 'ok');
          retryBtn.hidden = true;
        };

        ws.onmessage = function (evt) {
          try {
            var data = JSON.parse(evt.data);
            renderMessage(list, {
              sender: data.sender_type || 'owner',
              text: data.message || '',
              time: nowTime()
            });
          } catch (e) {
            // ignore invalid messages
          }
        };

        ws.onerror = function () {
          // wait for close
        };

        ws.onclose = function () {
          if (!opened && index < paths.length - 1) {
            index += 1;
            tryConnect();
            return;
          }
          setStatus('Ulanish uzildi', 'err');
          retryBtn.hidden = false;
        };
      }

      tryConnect();
    }

    function loadHistory() {
      var url = restBase + '/api/chat/rooms/' + roomId + '/messages/?visitor=' + encodeURIComponent(visitorToken);
      requestJson('GET', url).then(function (data) {
        data.forEach(function (m) {
          renderMessage(list, {
            sender: m.sender_type || 'owner',
            text: m.content || '',
            time: nowTime()
          });
        });
      }).catch(function () {
        // history is optional
      });
    }

    function startChat() {
      setStatus('Chat ochilmoqda...');
      var url = restBase + '/api/chat/start/';
      requestJson('POST', url, { user_id: userId, visitor_name: '' })
        .then(function (data) {
          roomId = data.room_id;
          visitorToken = data.visitor_token;
          loadHistory();
          connectWebSocket(data.ws_path || ('/ws/chat/' + roomId + '/'));
        })
        .catch(function (err) {
          setStatus(err.message || 'Chatni ochib bo‘lmadi', 'err');
          retryBtn.hidden = false;
        });
    }

    function sendMessage() {
      var text = (input.value || '').trim();
      if (!text) return;
      if (!ws || ws.readyState !== 1) {
        setStatus('Ulanish yo‘q. Qayta ulaning.', 'err');
        return;
      }
      ws.send(JSON.stringify({ message: text }));
      renderMessage(list, { sender: 'visitor', text: text, time: nowTime() });
      input.value = '';
    }

    btn.addEventListener('click', sendMessage);
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') sendMessage();
    });
    retryBtn.addEventListener('click', startChat);

    startChat();
  }

  window.CarInfoChat = { init: initChat };
})();
