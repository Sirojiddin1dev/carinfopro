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
      return res.text().then(function (text) {
        var data = null;
        if (text) {
          try {
            data = JSON.parse(text);
          } catch (e) {
            var parseErr = new Error('API JSON emas: ' + res.status);
            parseErr.raw = text;
            throw parseErr;
          }
        } else {
          data = {};
        }
        if (!res.ok) {
          var err = data && (data.detail || data.error) ? (data.detail || data.error) : ('Request failed (' + res.status + ')');
          throw new Error(err);
        }
        return data;
      });
    });
  }

  function initChat(opts) {
    var userId = opts.userId || 'unknown';
    var restBase = opts.restBase || '';
    var restBases = [restBase];
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
    var seen = {};
    var storeKey = 'carinfo_room_' + userId;

    if (userEl) userEl.textContent = userId;

    function formatTime(iso) {
      if (!iso) return nowTime();
      var d = new Date(iso);
      if (isNaN(d)) return nowTime();
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    function messageKey(msg) {
      if (msg.id) return 'id:' + msg.id;
      if (msg.created_at) return msg.sender + '|' + msg.created_at + '|' + msg.text;
      return msg.sender + '|' + msg.text + '|' + msg.time;
    }

    function addMessage(msg) {
      var key = messageKey(msg);
      if (seen[key]) return;
      seen[key] = true;
      renderMessage(list, msg);
    }

    function clearMessages() {
      list.innerHTML = '';
      seen = {};
    }

    function setStatus(text, kind) {
      statusEl.textContent = text;
      statusEl.className = 'status' + (kind ? ' ' + kind : '');
    }

    function connectWebSocket(wsPath) {
      var opened = false;

      function tryConnect() {
        var path = wsPath;
        var url = wsBase + path + '?visitor=' + encodeURIComponent(visitorToken);
        if (ws && (ws.readyState === 0 || ws.readyState === 1)) {
          ws.close();
        }
        ws = new WebSocket(url);

        ws.onopen = function () {
          opened = true;
          setStatus('Ulandi', 'ok');
          retryBtn.hidden = true;
        };

        ws.onmessage = function (evt) {
          try {
            var data = JSON.parse(evt.data);
            addMessage({
              id: data.id || null,
              sender: data.sender_type || 'owner',
              text: data.message || '',
              time: formatTime(data.created_at),
              created_at: data.created_at || null
            });
          } catch (e) {
            // ignore invalid messages
          }
        };

        ws.onerror = function () {
          // wait for close
        };

        ws.onclose = function () {
          setStatus('Ulanish uzildi', 'err');
          retryBtn.hidden = false;
        };
      }

      tryConnect();
    }

    function loadHistory() {
      var url = restBase + '/api/chat/rooms/' + roomId + '/messages/?visitor=' + encodeURIComponent(visitorToken);
      return requestJson('GET', url).then(function (data) {
        data.forEach(function (m) {
          addMessage({
            id: m.id || null,
            sender: m.sender_type || 'owner',
            text: m.content || '',
            time: formatTime(m.created_at),
            created_at: m.created_at || null
          });
        });
      });
    }

    function loadStoredRoom() {
      try {
        var raw = localStorage.getItem(storeKey);
        return raw ? JSON.parse(raw) : null;
      } catch (e) {
        return null;
      }
    }

    function saveStoredRoom() {
      localStorage.setItem(storeKey, JSON.stringify({
        roomId: roomId,
        visitorToken: visitorToken
      }));
    }

    function clearStoredRoom() {
      localStorage.removeItem(storeKey);
    }

    function startChat() {
      setStatus('Chat ochilmoqda...');
      retryBtn.hidden = true;
      var index = 0;

      function tryBase() {
        if (index >= restBases.length) {
          setStatus('Chatni ochib bo‘lmadi', 'err');
          retryBtn.hidden = false;
          return;
        }
        restBase = restBases[index];
        var url = restBase + '/api/chat/start/';
        requestJson('POST', url, { user_id: userId, visitor_name: '' })
          .then(function (data) {
            roomId = data.room_id;
            visitorToken = data.visitor_token;
            saveStoredRoom();
            clearMessages();
            loadHistory().then(function () {
              connectWebSocket(data.ws_path || ('/ws/chat/' + roomId + '/'));
            }).catch(function () {
              connectWebSocket(data.ws_path || ('/ws/chat/' + roomId + '/'));
            });
          })
          .catch(function () {
            index += 1;
            tryBase();
          });
      }

      tryBase();
    }

    function resumeChat() {
      var stored = loadStoredRoom();
      if (!stored || !stored.roomId || !stored.visitorToken) {
        startChat();
        return;
      }
      roomId = stored.roomId;
      visitorToken = stored.visitorToken;
      clearMessages();
      setStatus('Oldingi chat tiklanmoqda...');
      loadHistory().then(function () {
        connectWebSocket('/ws/chat/' + roomId + '/');
      }).catch(function () {
        clearStoredRoom();
        startChat();
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
      input.value = '';
    }

    btn.addEventListener('click', sendMessage);
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') sendMessage();
    });
    retryBtn.addEventListener('click', startChat);

    resumeChat();
  }

  window.CarInfoChat = { init: initChat };
})();
