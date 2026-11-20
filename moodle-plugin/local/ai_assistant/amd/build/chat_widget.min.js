define([], function() {
    function esc(s) {
        return (s || '').replace(/[&<>"']/g, function(c) {
            return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c];
        });
    }

    function renderInlineMarkdown(text) {
        var t = esc(text);
        t = t.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        t = t.replace(/\*(.+?)\*/g, '<em>$1</em>');
        t = t.replace(/\n/g, '<br>');
        return t;
    }

    function appendMessage(container, text, type, citations) {
        var msg = document.createElement('div');
        msg.className = 'local-ai-assistant-msg ' + type;
        msg.innerHTML = renderInlineMarkdown(text || '');
        if (citations && citations.length) {
            var cites = document.createElement('div');
            cites.className = 'local-ai-assistant-citations';
            var uniq = [];
            var seen = {};
            citations.forEach(function(c) {
                var name = c.source_name || 'Fuente';
                if (!seen[name]) { seen[name] = true; uniq.push(name); }
            });
            cites.innerHTML = '<small>Fuentes: ' + uniq.map(esc).join(', ') + '</small>';
            msg.appendChild(cites);
        }
        container.appendChild(msg);
        container.scrollTop = container.scrollHeight;
        return msg;
    }

    function proxyUrl(root, action) {
        var base = root.dataset.proxyurl || '';
        var sep = base.indexOf('?') === -1 ? '?' : '&';
        return base + sep + 'action=' + encodeURIComponent(action) +
            '&courseid=' + encodeURIComponent(root.dataset.courseid || '') +
            '&sesskey=' + encodeURIComponent(root.dataset.sesskey || '');
    }

    async function fetchHistory(root) {
        var res = await fetch(proxyUrl(root, 'history'));
        if (!res.ok) { throw new Error('history_failed'); }
        return res.json();
    }

    async function loadHistory(root, messages, state) {
        try {
            var data = await fetchHistory(root);
            if (data.conversation_id) { state.conversationId = data.conversation_id; }
            (data.messages || []).forEach(function(m) {
                if (m.role === 'user' || m.role === 'assistant') {
                    appendMessage(messages, m.content, m.role, m.citations || []);
                }
            });
        } catch (e) { /* ignore */ }
    }

    async function recoverLastAssistant(root, assistantMsg) {
        try {
            var data = await fetchHistory(root);
            var msgs = data.messages || [];
            for (var i = msgs.length - 1; i >= 0; i--) {
                if (msgs[i].role === 'assistant') {
                    assistantMsg.innerHTML = renderInlineMarkdown(msgs[i].content || '');
                    var citations = msgs[i].citations || [];
                    if (citations.length) {
                        var cites = document.createElement('div');
                        cites.className = 'local-ai-assistant-citations';
                        var uniq = []; var seen = {};
                        citations.forEach(function(c) { var n=c.source_name||'Fuente'; if(!seen[n]){seen[n]=true;uniq.push(n);} });
                        cites.innerHTML = '<small>Fuentes: ' + uniq.map(esc).join(', ') + '</small>';
                        assistantMsg.appendChild(cites);
                    }
                    return true;
                }
            }
        } catch (e) { /* ignore */ }
        return false;
    }

    async function sendChat(root, messages, state, text) {
        appendMessage(messages, text, 'user');
        var assistantMsg = appendMessage(messages, '', 'assistant');
        var full = '';
        var citations = [];
        try {
            var res = await fetch(proxyUrl(root, 'chat'), {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    message: text,
                    conversation_id: state.conversationId || null
                })
            });
            if (!res.ok || !res.body) {
                var recovered = await recoverLastAssistant(root, assistantMsg);
                if (!recovered) {
                    assistantMsg.innerHTML = renderInlineMarkdown('Error: no se pudo obtener respuesta (' + res.status + ').');
                }
                return;
            }
            var reader = res.body.getReader();
            var decoder = new TextDecoder('utf-8');
            var buffer = '';
            while (true) {
                var part = await reader.read();
                if (part.done) { break; }
                buffer += decoder.decode(part.value, {stream: true});
                var events = buffer.split('\n\n');
                buffer = events.pop() || '';
                events.forEach(function(evt) {
                    var lines = evt.split('\n');
                    var ev = 'message';
                    var data = '';
                    lines.forEach(function(line) {
                        if (line.indexOf('event:') === 0) { ev = line.slice(6).trim(); }
                        if (line.indexOf('data:') === 0) { data += line.slice(5).trim(); }
                    });
                    if (!data) { return; }
                    try {
                        var payload = JSON.parse(data);
                        if (ev === 'meta') {
                            if (payload.conversation_id) { state.conversationId = payload.conversation_id; }
                            if (payload.citations && payload.citations.length) { citations = payload.citations; }
                        } else if (ev === 'token') {
                            full += (payload.text || '');
                            assistantMsg.innerHTML = renderInlineMarkdown(full);
                            messages.scrollTop = messages.scrollHeight;
                        } else if (ev === 'error') {
                            full += (payload.message || 'Error');
                            assistantMsg.innerHTML = renderInlineMarkdown(full);
                        }
                    } catch (e) { /* ignore parse errors */ }
                });
            }
            if (!full.trim()) {
                var recoveredEnd = await recoverLastAssistant(root, assistantMsg);
                if (recoveredEnd) { return; }
            }
            if (citations.length) {
                assistantMsg.innerHTML = renderInlineMarkdown(full);
                var cites = document.createElement('div');
                cites.className = 'local-ai-assistant-citations';
                var uniq = []; var seen = {};
                citations.forEach(function(c) { var n=c.source_name||'Fuente'; if(!seen[n]){seen[n]=true;uniq.push(n);} });
                cites.innerHTML = '<small>Fuentes: ' + uniq.map(esc).join(', ') + '</small>';
                assistantMsg.appendChild(cites);
            }
        } catch (e) {
            var recoveredErr = await recoverLastAssistant(root, assistantMsg);
            if (!recoveredErr) {
                assistantMsg.innerHTML = renderInlineMarkdown('No se pudo conectar al servicio. Intenta de nuevo.');
            }
        }
    }

    function init() {
        var root = document.getElementById('local-ai-assistant-root');
        if (!root) { return; }
        var fab = document.getElementById('local-ai-assistant-fab');
        var panel = document.getElementById('local-ai-assistant-panel');
        var close = document.getElementById('local-ai-assistant-close');
        var form = document.getElementById('local-ai-assistant-form');
        var input = document.getElementById('local-ai-assistant-input');
        var messages = document.getElementById('local-ai-assistant-messages');
        var state = {conversationId: null, ready: false};

        fab.addEventListener('click', async function() {
            panel.classList.toggle('hidden');
            if (!panel.classList.contains('hidden') && !state.ready) {
                state.ready = true;
                await loadHistory(root, messages, state);
            }
        });
        close.addEventListener('click', function() { panel.classList.add('hidden'); });

        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            var text = (input.value || '').trim();
            if (!text) { return; }
            input.value = '';
            await sendChat(root, messages, state, text);
        });
    }

    return {init: init};
});