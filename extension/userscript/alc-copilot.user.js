// ==UserScript==
// @name         ALC Copilot
// @namespace    local.alc
// @version      1.0.0
// @description  AI Learning Copilot - explains content, MCQs, coding problems, and chats about the page. Works with the local backend on localhost:8000.
// @match        *://*/*
// @exclude      https://chrome.google.com/*
// @exclude      https://accounts.google.com/*
// @run-at       document-idle
// @grant        none
// ==/UserScript==

(function () {
  'use strict';

  const ALC_STYLES = `
:root {
  --alc-bg: #1e293b;
  --alc-bg-alt: #0f172a;
  --alc-primary: #3b82f6;
  --alc-primary-dark: #2563eb;
  --alc-secondary: #8b5cf6;
  --alc-text: #f1f5f9;
  --alc-text-muted: #94a3b8;
  --alc-border: #334155;
  --alc-success: #22c55e;
  --alc-warning: #eab308;
  --alc-error: #ef4444;
}

#alc-widget {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 2147483647;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 14px;
  line-height: 1.5;
  color: var(--alc-text);
}

#alc-toggle {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--alc-primary), var(--alc-secondary));
  color: white;
  border: none;
  cursor: pointer;
  font-size: 24px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s, box-shadow 0.2s;
  position: absolute;
  bottom: 0;
  right: 0;
}

#alc-toggle:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 16px rgba(59,130,246,0.4);
}

#alc-panel {
  position: absolute;
  bottom: 70px;
  right: 0;
  width: 420px;
  max-height: 600px;
  background: var(--alc-bg);
  border: 1px solid var(--alc-border);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5);
  display: none;
  flex-direction: column;
  overflow: hidden;
}

#alc-panel.open {
  display: flex;
}

#alc-header {
  padding: 16px 20px;
  background: var(--alc-bg-alt);
  border-bottom: 1px solid var(--alc-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  font-size: 15px;
  cursor: move;
  user-select: none;
}

#alc-header .alc-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

#alc-header .alc-close {
  background: none;
  border: none;
  color: var(--alc-text-muted);
  cursor: pointer;
  font-size: 20px;
  padding: 4px;
  line-height: 1;
}

#alc-header .alc-close:hover { color: var(--alc-text); }

#alc-body {
  padding: 16px 20px;
  overflow-y: auto;
  flex: 1;
  min-height: 200px;
  max-height: 480px;
}

#alc-body .alc-empty {
  text-align: center;
  color: var(--alc-text-muted);
  padding: 40px 0;
  font-size: 13px;
}

#alc-body .alc-empty strong {
  display: block;
  font-size: 16px;
  color: var(--alc-text);
  margin-bottom: 8px;
}

.alc-section {
  margin-bottom: 16px;
}

.alc-section-title {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--alc-text-muted);
  margin-bottom: 8px;
  font-weight: 600;
}

.alc-tools {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.alc-tool-btn {
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--alc-border);
  background: var(--alc-bg-alt);
  color: var(--alc-text);
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.alc-tool-btn:hover {
  border-color: var(--alc-primary);
  background: rgba(59,130,246,0.1);
}

.alc-tool-btn .alc-desc {
  font-size: 10px;
  color: var(--alc-text-muted);
  font-weight: 400;
}

.alc-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid var(--alc-border);
  border-top-color: var(--alc-primary);
  border-radius: 50%;
  animation: alc-spin 0.6s linear infinite;
  margin-right: 8px;
  vertical-align: middle;
}

@keyframes alc-spin { to { transform: rotate(360deg); } }

.alc-result {
  padding: 12px;
  border-radius: 8px;
  background: var(--alc-bg-alt);
  border: 1px solid var(--alc-border);
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.alc-result h4 {
  color: var(--alc-primary);
  margin: 0 0 4px 0;
  font-size: 13px;
}

.alc-result .alc-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--alc-text-muted);
  margin: 8px 0 4px;
  font-weight: 600;
}

.alc-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  margin: 2px 4px 2px 0;
}

.alc-badge.blue { background: rgba(59,130,246,0.2); color: #93c5fd; }
.alc-badge.green { background: rgba(34,197,94,0.2); color: #86efac; }
.alc-badge.yellow { background: rgba(234,179,8,0.2); color: #fde047; }
.alc-badge.purple { background: rgba(139,92,246,0.2); color: #c4b5fd; }

.alc-option {
  padding: 8px 12px;
  margin: 4px 0;
  border-radius: 6px;
  border-left: 3px solid var(--alc-border);
  background: rgba(0,0,0,0.2);
  font-size: 13px;
}

.alc-option.correct {
  border-left-color: var(--alc-success);
  background: rgba(34,197,94,0.1);
}

.alc-option.wrong {
  border-left-color: var(--alc-error);
  background: rgba(239,68,68,0.1);
}

.alc-option .alc-label-tag {
  font-weight: 600;
  color: var(--alc-primary);
  margin-right: 6px;
}

.alc-option .alc-check {
  float: right;
  font-size: 14px;
}

.alc-footer-text {
  font-size: 10px;
  text-align: center;
  color: var(--alc-text-muted);
  padding: 8px;
  border-top: 1px solid var(--alc-border);
}

.alc-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.alc-actions button {
  padding: 6px 12px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
}

.alc-actions .alc-btn-primary {
  background: var(--alc-primary);
  color: white;
}

.alc-actions .alc-btn-primary:hover {
  background: var(--alc-primary-dark);
}

.alc-actions .alc-btn-secondary {
  background: var(--alc-bg-alt);
  color: var(--alc-text);
  border: 1px solid var(--alc-border);
}

.alc-actions .alc-btn-secondary:hover {
  border-color: var(--alc-text-muted);
}

.alc-tab {
  padding: 4px 10px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  color: var(--alc-text-muted);
  background: transparent;
  transition: all 0.2s;
}

.alc-tab:hover {
  background: rgba(59,130,246,0.1);
  color: var(--alc-text);
}

#alc-chat-view {
  display: none;
  flex-direction: column;
  height: 100%;
}

#alc-chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
  min-height: 300px;
  max-height: 400px;
}

#alc-input:focus {
  border-color: var(--alc-primary);
  box-shadow: 0 0 0 2px rgba(59,130,246,0.2);
}

#alc-resize-handle {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 20px;
  height: 20px;
  cursor: nwse-resize;
  color: var(--alc-text-muted);
  font-size: 12px;
  display: flex;
  align-items: flex-end;
  justify-content: flex-end;
  padding: 0 3px 1px 0;
  user-select: none;
  z-index: 10;
}

#alc-resize-handle:hover {
  color: var(--alc-primary);
}
`;

  const styleEl = document.createElement('style');
  styleEl.textContent = ALC_STYLES;
  document.head.appendChild(styleEl);

const API_BASE = 'http://localhost:8000';

const html = `
<div id="alc-widget">
  <div id="alc-panel">
    <div id="alc-header">
      <span class="alc-title" title="Drag to move · double-click to reset position">⚡ ALC Copilot</span>
      <div style="display:flex;gap:4px;">
        <button class="alc-tab" id="alc-tab-tools" style="background:rgba(59,130,246,0.2);color:var(--alc-primary);">Tools</button>
        <button class="alc-tab" id="alc-tab-chat">Chat</button>
        <button class="alc-close" id="alc-close-btn">&times;</button>
      </div>
    </div>
    <div id="alc-body">
      <div id="alc-tools-view">
        <div class="alc-empty" id="alc-empty-state">
          <strong>How can I help you learn?</strong>
          Select text on the page or use tools below.
        </div>
        <div id="alc-content"></div>
        <div class="alc-section">
          <div class="alc-section-title">Tools</div>
          <div class="alc-tools">
            <button class="alc-tool-btn" data-action="explain">
              <span>🔍 Explain</span>
              <span class="alc-desc">Explain selected text</span>
            </button>
            <button class="alc-tool-btn" data-action="mcq-explain">
              <span>✅ Explain MCQ</span>
              <span class="alc-desc">Analyze question & options</span>
            </button>
            <button class="alc-tool-btn" data-action="coding-help">
              <span>💻 Coding Help</span>
              <span class="alc-desc">Coding problem help</span>
            </button>
            <button class="alc-tool-btn" data-action="generate-notes">
              <span>📝 Generate Notes</span>
              <span class="alc-desc">Summarize this page</span>
            </button>
          </div>
        </div>
      </div>
      <div id="alc-chat-view" style="display:none;flex-direction:column;height:100%;">
        <div id="alc-chat-messages" style="flex:1;overflow-y:auto;padding:8px 0;min-height:300px;max-height:400px;"></div>
        <div style="display:flex;gap:8px;padding-top:8px;border-top:1px solid var(--alc-border);">
          <input id="alc-chat-input" type="text" placeholder="Ask about this page..." style="flex:1;padding:8px 12px;border-radius:8px;border:1px solid var(--alc-border);background:var(--alc-bg-alt);color:var(--alc-text);font-size:13px;outline:none;">
          <button id="alc-chat-clear" title="Clear chat" style="padding:8px 10px;border-radius:8px;border:1px solid var(--alc-border);background:var(--alc-bg-alt);color:var(--alc-text-muted);cursor:pointer;font-size:13px;">↺</button>
          <button id="alc-chat-send" style="padding:8px 16px;border-radius:8px;border:none;background:var(--alc-primary);color:white;cursor:pointer;font-weight:600;">Send</button>
        </div>
      </div>
    </div>
    <div class="alc-footer-text">AI Learning Copilot · localhost:8000</div>
    <div id="alc-resize-handle" title="Drag to resize">↘</div>
  </div>
  <button id="alc-toggle">⚡</button>
</div>
`;

let chatHistory = [];
let chatInitialized = false;
let lastUrl = location.href;
let lastPageHash = '';
let mutationTimer = null;

function injectWidget() {
  if (document.getElementById('alc-widget')) return;
  const container = document.createElement('div');
  container.innerHTML = html;
  document.body.appendChild(container);

  const toggle = document.getElementById('alc-toggle');
  const panel = document.getElementById('alc-panel');
  const closeBtn = document.getElementById('alc-close-btn');

  toggle.onclick = () => {
    panel.classList.toggle('open');
    toggle.textContent = panel.classList.contains('open') ? '✕' : '⚡';
  };

  closeBtn.onclick = () => {
    panel.classList.remove('open');
    toggle.textContent = '⚡';
  };

  document.getElementById('alc-tab-tools').onclick = () => switchTab('tools');
  document.getElementById('alc-tab-chat').onclick = () => switchTab('chat');
  document.getElementById('alc-chat-send').onclick = sendChatMessage;
  document.getElementById('alc-chat-clear').onclick = () => resetChat(false);
  document.getElementById('alc-chat-input').onkeydown = (e) => { if (e.key === 'Enter') sendChatMessage(); };

  document.querySelectorAll('.alc-tool-btn[data-action]').forEach(btn => {
    btn.onclick = () => doAction(btn.dataset.action);
  });

  enableResize();
  enableDrag();
  startPageWatcher();
}

function getPageText() {
  const parts = [];
  try {
    const main = document.querySelector('main') || document.querySelector('#root') || document.body;
    parts.push(main.innerText || '');
  } catch (e) { /* ignore */ }
  document.querySelectorAll('iframe').forEach(f => {
    try {
      parts.push(f.contentDocument.body.innerText || '');
    } catch (e) { /* cross-origin, ignore */ }
  });
  return parts.join('\n');
}

function guessLanguage(el) {
  const cls = (el.className || '').toString();
  const m = cls.match(/language-([\w+#-]+)/i);
  if (m) return m[1].toLowerCase();
  if (/python|lang-py|language-py/.test(cls)) return 'python';
  if (/javascript|lang-js|language-js/.test(cls)) return 'javascript';
  if (/\bcpp\b|\bc\+\+/.test(cls)) return 'cpp';
  if (/\bjava\b/.test(cls)) return 'java';
  if (/\btypescript|\bts\b/.test(cls)) return 'typescript';
  return '';
}

function collectCodeInDoc(doc) {
  const seen = new Set();
  const blocks = [];

  const add = (text, lang, order) => {
    const t = (text || '').trim();
    if (!t || t.length < 3 || seen.has(t)) return;
    seen.add(t);
    blocks.push({ code: t, lang, order });
  };

  doc.querySelectorAll('pre').forEach((pre, i) => {
    const codeEl = pre.querySelector('code');
    add(pre.innerText, codeEl ? guessLanguage(codeEl) : '', i * 100);
  });

  doc.querySelectorAll('code').forEach((el, i) => {
    if (el.closest('pre')) return;
    add(el.innerText, guessLanguage(el), 1000 + i * 100);
  });

  doc.querySelectorAll('.view-lines, .cm-content, .ace_content, .cm-editor').forEach((el, i) => {
    const lineEls = el.querySelectorAll('.view-line, .cm-line, .ace_line');
    const lines = [];
    lineEls.forEach((lineEl, j) => {
      if (j > 500) return;
      const lineText = lineEl.innerText || lineEl.textContent || '';
      if (lineText) lines.push(lineText);
    });
    if (lines.length) add(lines.join('\n'), '', 2000 + i * 100);
  });

  doc.querySelectorAll('textarea').forEach((el, i) => {
    if (el.value && el.value.length > 20) add(el.value, '', 3000 + i * 100);
  });

  return blocks;
}

function getCodeBlocks() {
  let blocks = collectCodeInDoc(document);
  document.querySelectorAll('iframe').forEach(f => {
    try {
      blocks = blocks.concat(collectCodeInDoc(f.contentDocument));
    } catch (e) { /* cross-origin, ignore */ }
  });

  blocks.sort((a, b) => a.order - b.order);
  const parts = [];
  let size = 0;
  for (const b of blocks) {
    if (parts.length >= 10 || size + b.code.length > 15000) break;
    const lang = b.lang ? ` (${b.lang})` : '';
    parts.push(`=== Code block ${parts.length + 1}${lang} ===\n${b.code}`);
    size += b.code.length;
  }
  return parts.join('\n\n');
}

function pageHash() {
  let hash = 0;
  const sample = getPageText().slice(0, 4000);
  for (let i = 0; i < sample.length; i++) {
    hash = ((hash << 5) - hash) + sample.charCodeAt(i);
    hash |= 0;
  }
  return hash;
}

function startPageWatcher() {
  const origPushState = history.pushState;
  history.pushState = function (...args) {
    const r = origPushState.apply(this, args);
    setTimeout(() => onPageChanged(true), 200);
    return r;
  };
  window.addEventListener('popstate', () => setTimeout(() => onPageChanged(true), 200));

  new MutationObserver(() => {
    if (mutationTimer) return;
    mutationTimer = setTimeout(() => {
      mutationTimer = null;
      const hash = pageHash();
      if (hash !== lastPageHash) {
        lastPageHash = hash;
        onPageChanged(false);
      }
    }, 700);
  }).observe(document.body, { childList: true, subtree: true });

  setInterval(() => {
    const hash = pageHash();
    if (hash !== lastPageHash) {
      lastPageHash = hash;
      onPageChanged(false);
    }
  }, 3000);
}

function onPageChanged(isUrlChange) {
  const urlChanged = location.href !== lastUrl;
  if (urlChanged) {
    lastUrl = location.href;
  }
  const input = document.getElementById('alc-chat-input');
  const isTyping = input && document.activeElement === input && input.value.trim();
  if (isTyping) return;

  chatHistory = [];
  chatInitialized = false;
  const msgContainer = document.getElementById('alc-chat-messages');
  if (!msgContainer) return;
  const panel = document.getElementById('alc-panel');
  const chatOpen = panel && panel.classList.contains('open') &&
    document.getElementById('alc-chat-view').style.display !== 'none';

  if (chatOpen) {
    const label = urlChanged || isUrlChange ? 'New page detected — chat reset. Ask about this question.' : 'Page content changed — chat reset.';
    msgContainer.innerHTML = `<div style="text-align:center;color:var(--alc-text-muted);padding:20px;font-size:13px;">${label}</div>`;
  } else {
    msgContainer.innerHTML = '';
  }
  if (input) input.value = '';
}

function resetChat(showMsg) {
  chatHistory = [];
  chatInitialized = false;
  const msgContainer = document.getElementById('alc-chat-messages');
  if (!msgContainer) return;
  const panel = document.getElementById('alc-panel');
  const chatOpen = panel && panel.classList.contains('open') &&
    document.getElementById('alc-chat-view').style.display !== 'none';
  if (showMsg && chatOpen) {
    msgContainer.innerHTML = '<div style="text-align:center;color:var(--alc-text-muted);padding:20px;font-size:13px;">Chat cleared. Ask anything.</div>';
  } else {
    msgContainer.innerHTML = '';
  }
  const input = document.getElementById('alc-chat-input');
  if (input) input.value = '';
}

function switchTab(tab) {
  const toolsView = document.getElementById('alc-tools-view');
  const chatView = document.getElementById('alc-chat-view');
  const tabTools = document.getElementById('alc-tab-tools');
  const tabChat = document.getElementById('alc-tab-chat');

  if (tab === 'tools') {
    toolsView.style.display = 'block';
    chatView.style.display = 'none';
    tabTools.style.background = 'rgba(59,130,246,0.2)';
    tabTools.style.color = 'var(--alc-primary)';
    tabChat.style.background = 'transparent';
    tabChat.style.color = 'var(--alc-text-muted)';
  } else {
    toolsView.style.display = 'none';
    chatView.style.display = 'flex';
    tabChat.style.background = 'rgba(59,130,246,0.2)';
    tabChat.style.color = 'var(--alc-primary)';
    tabTools.style.background = 'transparent';
    tabTools.style.color = 'var(--alc-text-muted)';
    if (!chatInitialized) {
      const msgContainer = document.getElementById('alc-chat-messages');
      msgContainer.innerHTML = '<div style="text-align:center;color:var(--alc-text-muted);padding:20px;font-size:13px;">I can see this page. Ask any question about the lesson you\'re viewing.</div>';
      chatInitialized = true;
    }
    setTimeout(() => document.getElementById('alc-chat-input').focus(), 100);
  }
}

function enableResize() {
  const panel = document.getElementById('alc-panel');
  const handle = document.getElementById('alc-resize-handle');
  const body = document.getElementById('alc-body');

  try {
    const saved = JSON.parse(localStorage.getItem('alc_size'));
    if (saved && saved.width && saved.height) {
      panel.style.width = saved.width + 'px';
      panel.style.height = saved.height + 'px';
      body.style.maxHeight = 'none';
    }
  } catch (e) { /* ignore */ }

  handle.addEventListener('mousedown', (e) => {
    e.preventDefault();
    e.stopPropagation();
    const startX = e.clientX;
    const startY = e.clientY;
    const startW = panel.offsetWidth;
    const startH = panel.offsetHeight;

    const onMove = (ev) => {
      const w = Math.min(Math.max(startW + (ev.clientX - startX), 300), window.innerWidth - 40);
      const h = Math.min(Math.max(startH + (ev.clientY - startY), 350), window.innerHeight - 80);
      panel.style.width = w + 'px';
      panel.style.height = h + 'px';
      body.style.maxHeight = 'none';
    };
    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      try {
        localStorage.setItem('alc_size', JSON.stringify({
          width: panel.offsetWidth,
          height: panel.offsetHeight,
        }));
      } catch (err) { /* ignore */ }
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  });
}

function enableDrag() {
  const widget = document.getElementById('alc-widget');
  const header = document.getElementById('alc-header');
  const title = header.querySelector('.alc-title');

  try {
    const saved = JSON.parse(localStorage.getItem('alc_pos'));
    if (saved && typeof saved.left === 'number' && typeof saved.top === 'number') {
      widget.style.left = saved.left + 'px';
      widget.style.top = saved.top + 'px';
      widget.style.bottom = 'auto';
      widget.style.right = 'auto';
    }
  } catch (e) { /* ignore */ }

  header.addEventListener('mousedown', (e) => {
    if (e.target.closest('button')) return;
    e.preventDefault();
    const startX = e.clientX;
    const startY = e.clientY;
    const rect = widget.getBoundingClientRect();
    const offsetX = startX - rect.left;
    const offsetY = startY - rect.top;
    widget.style.bottom = 'auto';
    widget.style.right = 'auto';

    const onMove = (ev) => {
      const x = Math.min(Math.max(ev.clientX - offsetX, 10), window.innerWidth - 70);
      const y = Math.min(Math.max(ev.clientY - offsetY, 10), window.innerHeight - 70);
      widget.style.left = x + 'px';
      widget.style.top = y + 'px';
    };
    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      try {
        localStorage.setItem('alc_pos', JSON.stringify({
          left: widget.offsetLeft,
          top: widget.offsetTop,
        }));
      } catch (err) { /* ignore */ }
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  });

  title.addEventListener('dblclick', () => {
    widget.style.left = '';
    widget.style.top = '';
    widget.style.bottom = '20px';
    widget.style.right = '20px';
    try { localStorage.removeItem('alc_pos'); } catch (e) { /* ignore */ }
  });
}

function showLoading(msg = 'Thinking...') {
  const content = document.getElementById('alc-content');
  const emptyState = document.getElementById('alc-empty-state');
  if (emptyState) emptyState.style.display = 'none';
  content.innerHTML = `<div class="alc-result"><span class="alc-spinner"></span> ${msg}</div>`;
}

function showError(msg) {
  const content = document.getElementById('alc-content');
  content.innerHTML = `<div class="alc-result" style="border-color:var(--alc-error);color:var(--alc-error);">${escapeHtml(msg)}</div>`;
}

function showResult(htmlContent) {
  const content = document.getElementById('alc-content');
  content.innerHTML = `<div class="alc-result">${htmlContent}</div>`;
  switchTab('tools');
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

async function doAction(action) {
  const sel = window.getSelection().toString().trim();
  const text = sel || getPageText();
  const title = document.title;
  const codeContext = getCodeBlocks();

  showLoading();

  try {
    const res = await fetch(`${API_BASE}/api/extension/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action,
        text: text.slice(0, 6000),
        title,
        code_context: codeContext || undefined,
      }),
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Request failed');
    const data = await res.json();
    renderResult(action, data);
  } catch (e) {
    const msg = e.message.includes('fetch') ? 'Cannot reach backend. Is it running on localhost:8000?' : e.message;
    showError(msg);
  }
}

function renderResult(action, data) {
  if (data.error) { showError(data.error); return; }

  let html = '';

  if (action === 'explain') {
    html += `<div>${escapeHtml(data.response || data.explanation || '(no response)')}</div>`;
  }

  else if (action === 'coding-help') {
    if (data.response) {
      html += `<div style="white-space:pre-wrap;">${escapeHtml(data.response)}</div>`;
    } else {
      if (data.explanation) html += `<div class="alc-label">Explanation</div><div>${escapeHtml(data.explanation)}</div>`;
      if (data.algorithms) html += renderBadges('Algorithms', data.algorithms, 'blue');
      if (data.data_structures) html += renderBadges('Data Structures', data.data_structures, 'purple');
      if (data.approach) html += `<div class="alc-label">Approach</div><div>${escapeHtml(data.approach)}</div>`;
    }
  }

  else if (action === 'mcq-explain' && data.options) {
    html += `<div style="font-weight:600;margin-bottom:8px;">${escapeHtml(data.question_text || 'Question')}</div>`;
    (data.options || []).forEach(o => {
      const cls = o.is_correct ? 'correct' : 'wrong';
      const check = o.is_correct ? '✅' : '❌';
      html += `<div class="alc-option ${cls}"><span class="alc-label-tag">${escapeHtml(o.label)}.</span> ${escapeHtml(o.text)} <span class="alc-check">${check}</span>`;
      if (o.explanation) html += `<div style="font-size:12px;color:var(--alc-text-muted);margin-top:4px;">${escapeHtml(o.explanation)}</div>`;
      html += `</div>`;
    });
    if (data.suggested_answer) html += `<div style="margin-top:8px;"><span class="alc-label">Suggested:</span> <strong>${escapeHtml(data.suggested_answer)}</strong></div>`;
    if (data.overall_reasoning) html += `<div class="alc-label">Reasoning</div><div>${escapeHtml(data.overall_reasoning)}</div>`;
  }

  else if (action === 'generate-notes' && data.response) {
    html += `<div style="white-space:pre-wrap;">${escapeHtml(data.response)}</div>`;
  }

  else if (data.response) {
    html += `<div style="white-space:pre-wrap;">${escapeHtml(data.response)}</div>`;
  }

  else {
    html += `<div>${escapeHtml(JSON.stringify(data, null, 2).slice(0, 2000))}</div>`;
  }

  showResult(html);
}

function renderBadges(label, items, color) {
  return `<div class="alc-label">${label}</div><div>${items.map(i => `<span class="alc-badge ${color}">${escapeHtml(i)}</span>`).join('')}</div>`;
}

async function sendChatMessage() {
  const input = document.getElementById('alc-chat-input');
  const msgContainer = document.getElementById('alc-chat-messages');
  const text = input.value.trim();
  if (!text) return;

  input.value = '';
  if (msgContainer.children.length === 1 && msgContainer.children[0].dataset.placeholder) {
    msgContainer.innerHTML = '';
  }

  msgContainer.innerHTML += `<div style="text-align:right;margin:4px 0;"><span style="display:inline-block;padding:6px 12px;border-radius:12px 12px 4px 12px;background:var(--alc-primary);color:white;font-size:13px;max-width:80%;word-break:break-word;">${escapeHtml(text)}</span></div>`;

  const loadingId = 'msg-' + Date.now();
  msgContainer.innerHTML += `<div id="${loadingId}" style="text-align:left;margin:4px 0;"><span style="display:inline-block;padding:6px 12px;border-radius:12px 12px 12px 4px;background:var(--alc-bg-alt);border:1px solid var(--alc-border);font-size:13px;"><span class="alc-spinner"></span> Thinking...</span></div>`;
  msgContainer.scrollTop = msgContainer.scrollHeight;

  chatHistory.push({ role: "user", content: text });

  const pageContext = getPageText().slice(0, 12000);
  const codeContext = getCodeBlocks();
  const codeIntent = /\b(code|write|implement|solve|solution|function|program|snippet|fix|syntax)\b/i.test(text);

  try {
    const res = await fetch(`${API_BASE}/api/extension/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'chat',
        text,
        messages: chatHistory,
        page_context: pageContext,
        code_context: codeContext || undefined,
        code_intent: codeIntent,
      }),
    });
    if (!res.ok) throw new Error('Request failed');
    const data = await res.json();
    const reply = data.response || '(no response)';

    document.getElementById(loadingId)?.remove();
    msgContainer.innerHTML += `<div style="text-align:left;margin:4px 0;"><span style="display:inline-block;padding:6px 12px;border-radius:12px 12px 12px 4px;background:var(--alc-bg-alt);border:1px solid var(--alc-border);font-size:13px;max-width:80%;word-break:break-word;white-space:pre-wrap;">${escapeHtml(reply)}</span></div>`;
    chatHistory.push({ role: "assistant", content: reply });
    msgContainer.scrollTop = msgContainer.scrollHeight;
  } catch (e) {
    document.getElementById(loadingId)?.remove();
    const errMsg = e.message.includes('fetch') ? 'Backend offline. Is the server running?' : e.message;
    msgContainer.innerHTML += `<div style="text-align:left;margin:4px 0;"><span style="display:inline-block;padding:6px 12px;border-radius:12px;background:rgba(239,68,68,0.1);border:1px solid var(--alc-error);color:var(--alc-error);font-size:13px;">Error: ${escapeHtml(errMsg)}</span></div>`;
  }
}

function init() {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectWidget);
  } else {
    injectWidget();
  }
}

init();
})();
