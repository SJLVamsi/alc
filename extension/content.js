const API_BASE = 'http://localhost:8000';

// --- capture limits (Spec A) ---
const MAX_QUESTION_CHARS = 2000;
const MAX_CONTEXT_CHARS = 4000;
const MAX_VISIBLE_CHARS = 3000;
const MAX_PAGE_CHARS = 12000;
const SELECTION_MIN_CHARS = 10;
const SELECTION_TTL_MS = 2 * 60 * 1000;

const SKIP_SELECTOR = 'nav, header, footer, aside, [role="navigation"], [role="banner"]';
const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'NAV', 'HEADER', 'FOOTER', 'ASIDE']);

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
        <div class="alc-capture-toggle">
          <label title="Show the exact text sent to the AI">
            <input type="checkbox" id="alc-preview-toggle"> Preview captured text
          </label>
        </div>
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
let mutationTimer = null;
let lastSelection = { text: '', ts: 0 };
let lastQuestionSignature = '';
let previewCapture = false;
let lastCapture = null;

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

  const previewToggle = document.getElementById('alc-preview-toggle');
  try { previewCapture = localStorage.getItem('alc_preview') === '1'; } catch (e) { /* ignore */ }
  if (previewToggle) {
    previewToggle.checked = previewCapture;
    previewToggle.onchange = () => {
      previewCapture = previewToggle.checked;
      try { localStorage.setItem('alc_preview', previewCapture ? '1' : '0'); } catch (e) { /* ignore */ }
      if (previewCapture) showCapturePreview();
    };
  }

  // Track the last real selection: clicking a panel button collapses it.
  ['mouseup', 'keyup', 'selectionchange'].forEach(evt =>
    document.addEventListener(evt, rememberSelection, true)
  );
}

// --- capture: shared helpers ---------------------------------------------

function isInWidget(el) {
  if (!el) return false;
  if (el.id === 'alc-widget') return true;
  const node = el.nodeType === 1 ? el : el.parentElement;
  return !!(node && node.closest && node.closest('#alc-widget'));
}

function stripOptionMarker(text) {
  return (text || '')
    .trim()
    .replace(/^\(?([A-Za-z]|\d{1,2})[.):]\s*/, '')
    .trim();
}

function cssEscape(value) {
  if (window.CSS && CSS.escape) return CSS.escape(value);
  return String(value).replace(/([^\w-])/g, '\\$1');
}

// --- capture: selection --------------------------------------------------

function rememberSelection() {
  let sel = '';
  try {
    sel = (window.getSelection() || '').toString().trim();
  } catch (e) {
    sel = '';
  }
  if (sel) lastSelection = { text: sel, ts: Date.now() };
}

function currentSelection() {
  let sel = '';
  try {
    sel = (window.getSelection() || '').toString().trim();
  } catch (e) {
    sel = '';
  }
  if (sel.length >= SELECTION_MIN_CHARS) return sel;
  // Button clicks steal focus and collapse the selection, so fall back to the
  // most recent non-empty selection if it's still fresh.
  if (Date.now() - lastSelection.ts < SELECTION_TTL_MS) return lastSelection.text;
  return '';
}

// --- capture: MCQ detection ----------------------------------------------

function collectOptionGroups(root) {
  const groups = [];

  const byName = new Map();
  root.querySelectorAll('input[type="radio"], input[type="checkbox"]').forEach(el => {
    const name = el.getAttribute('name');
    if (!name) return;
    const key = `${el.type}|${name}`;
    if (!byName.has(key)) byName.set(key, []);
    byName.get(key).push(el);
  });
  byName.forEach(els => { if (els.length >= 2) groups.push(els); });

  root.querySelectorAll('[role="radiogroup"]').forEach(rg => {
    const opts = Array.from(rg.querySelectorAll('[role="radio"]'));
    if (opts.length >= 2) groups.push(opts);
  });

  root.querySelectorAll('[class]').forEach(el => {
    const cls = (el.className || '').toString();
    if (!/option|choice|answer/i.test(cls)) return;
    const parent = el.parentElement;
    if (!parent) return;
    const siblings = Array.from(parent.children).filter(s =>
      /option|choice|answer/i.test((s.className || '').toString())
    );
    if (siblings.length >= 2 && siblings.length <= 6) groups.push(siblings);
  });

  // Drop groups detected twice (same elements, e.g. class + role heuristics).
  const seen = new Set();
  return groups.filter(g => {
    const sig = g.map(e => {
      if (!e.__alcUid) e.__alcUid = Math.random().toString(36).slice(2);
      return e.__alcUid;
    }).sort().join(',');
    if (seen.has(sig)) return false;
    seen.add(sig);
    return true;
  });
}

function groupVisibility(els) {
  const rects = els.map(e => e.getBoundingClientRect());
  const onscreen = rects.filter(r => r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < window.innerHeight);
  if (!onscreen.length) return null;
  const centre = onscreen.reduce((a, r) => a + r.top + r.height / 2, 0) / onscreen.length;
  return {
    fullyVisible: onscreen.length === rects.length,
    distance: Math.abs(centre - window.innerHeight / 2),
  };
}

function textBlockBefore(node, boundary) {
  let cur = node;
  while (cur && cur !== boundary) {
    let sib = cur.previousElementSibling;
    while (sib) {
      const text = (sib.innerText || sib.textContent || '').trim();
      if (text && !isInWidget(sib)) return text;
      sib = sib.previousElementSibling;
    }
    cur = cur.parentElement;
  }
  return '';
}

function optionTextFor(el) {
  let text = '';
  if (el.tagName === 'INPUT') {
    if (el.id) {
      const lbl = document.querySelector(`label[for="${cssEscape(el.id)}"]`);
      if (lbl) text = lbl.innerText || lbl.textContent || '';
    }
    if (!text) {
      const wrap = el.closest('label');
      if (wrap) text = wrap.innerText || wrap.textContent || '';
    }
    if (!text && el.parentElement) {
      text = el.parentElement.innerText || el.parentElement.textContent || '';
    }
  } else {
    text = el.innerText || el.textContent || '';
  }
  return stripOptionMarker(text);
}

function detectMCQGroup() {
  const groups = collectOptionGroups(document);
  let best = null;

  for (const els of groups) {
    const vis = groupVisibility(els);
    if (!vis) continue;
    const score = (vis.fullyVisible ? 0 : 1e6) + vis.distance;
    if (!best || score < best.score) best = { els, score };
  }
  if (!best) return null;

  // Smallest ancestor holding the whole group plus one preceding text block.
  const first = best.els[0];
  let container = null;
  let stem = '';
  let cur = first;
  while (cur && cur !== document.body) {
    cur = cur.parentElement;
    if (!cur) break;
    if (!best.els.every(e => cur.contains(e))) continue;
    const before = textBlockBefore(first, cur);
    if (before) { container = cur; stem = before; break; }
    if (container === null) container = cur; // fallback: group-only ancestor
  }
  if (!container) return null;

  const options = best.els.map(optionTextFor).filter(t => t.length > 0);
  if (options.length < 2) return null;

  const inViewport = best.els[0].getBoundingClientRect();
  if (inViewport.top > window.innerHeight || inViewport.bottom < 0) return null;

  return {
    questionText: (container.innerText || container.textContent || stem).trim(),
    stem,
    options,
  };
}

// --- capture: visible text -----------------------------------------------

function viewportText(limit = MAX_VISIBLE_CHARS) {
  const parts = [];
  let total = 0;
  const walker = document.createTreeWalker(document.body || document.documentElement, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const parent = node.parentElement;
      if (!parent) return NodeFilter.FILTER_REJECT;
      if (SKIP_TAGS.has(parent.tagName)) return NodeFilter.FILTER_REJECT;
      if (isInWidget(parent)) return NodeFilter.FILTER_REJECT;
      if (parent.closest(SKIP_SELECTOR)) return NodeFilter.FILTER_REJECT;
      const text = (node.nodeValue || '').trim();
      if (!text) return NodeFilter.FILTER_REJECT;
      const rect = parent.getBoundingClientRect();
      if (!rect.width || !rect.height) return NodeFilter.FILTER_REJECT;
      if (rect.bottom < 0 || rect.top > window.innerHeight) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    },
  });

  let node;
  while ((node = walker.nextNode())) {
    const text = (node.nodeValue || '').trim();
    if (!text) continue;
    parts.push(text);
    total += text.length + 1;
    if (total >= limit) break;
  }
  return parts.join(' ').slice(0, limit);
}

function nearestHeading() {
  const headings = Array.from(document.querySelectorAll('h1, h2, h3'));
  let best = '';
  for (const h of headings) {
    const rect = h.getBoundingClientRect();
    if (rect.bottom <= 0 || isInWidget(h)) continue;
    const text = (h.innerText || h.textContent || '').trim();
    if (text) { best = text; break; }
  }
  return best;
}

function getQuestionContext() {
  const title = document.title;
  const url = location.href;
  const selection = currentSelection();

  if (selection) {
    return {
      source: 'selection',
      label: 'selection',
      question_text: selection.slice(0, MAX_QUESTION_CHARS),
      options: [],
      context_text: viewportText(MAX_CONTEXT_CHARS),
      page_title: title,
      url,
    };
  }

  const mcq = detectMCQGroup();
  if (mcq) {
    return {
      source: 'mcq',
      label: 'detected question',
      question_text: mcq.questionText.slice(0, MAX_QUESTION_CHARS),
      options: mcq.options,
      context_text: mcq.questionText.slice(0, MAX_CONTEXT_CHARS),
      page_title: title,
      url,
    };
  }

  const visible = viewportText(MAX_VISIBLE_CHARS);
  const heading = nearestHeading();
  const context = [heading, visible].filter(Boolean).join('\n\n');
  return {
    source: 'visible',
    label: 'visible text',
    question_text: visible.slice(0, MAX_QUESTION_CHARS),
    options: [],
    context_text: context.slice(0, MAX_CONTEXT_CHARS),
    page_title: title,
    url,
  };
}

function getPageText() {
  const root = document.querySelector('main') || document.querySelector('#root') || document.body;
  if (!root) return '';

  let text = '';
  let clone = null;
  try { clone = root.cloneNode(true); } catch (e) { clone = null; }

  if (clone) {
    clone.querySelectorAll('#alc-widget').forEach(el => el.remove());
    clone.querySelectorAll('script, style, noscript, template, nav, footer, aside, [role="navigation"], [role="banner"]')
      .forEach(el => el.remove());
    text = (clone.innerText || clone.textContent || '').trim();
  } else {
    text = (root.innerText || '').trim();
  }

  const parts = [text];
  document.querySelectorAll('iframe').forEach(f => {
    try {
      const doc = f.contentDocument;
      if (doc && doc.body) {
        const t = (doc.body.innerText || '').trim();
        if (t) parts.push(t);
      }
    } catch (e) { /* cross-origin, ignore */ }
  });
  return parts.filter(Boolean).join('\n');
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

function hashString(text) {
  let hash = 0;
  for (let i = 0; i < text.length; i++) {
    hash = ((hash << 5) - hash) + text.charCodeAt(i);
    hash |= 0;
  }
  return String(hash);
}

// Cheap fingerprint of whatever the panel would currently act on: the live
// selection, else the detected MCQ. Deliberately avoids the viewport walk so
// it stays affordable on every debounced mutation.
function questionFingerprint() {
  const sel = currentSelection();
  if (sel) return `sel:${hashString(sel)}`;
  const mcq = detectMCQGroup();
  if (mcq) return `mcq:${hashString(mcq.questionText)}`;
  return '';
}

function isWidgetMutation(mutation) {
  return isInWidget(mutation.target);
}

function startPageWatcher() {
  const origPushState = history.pushState;
  history.pushState = function (...args) {
    const r = origPushState.apply(this, args);
    setTimeout(checkPage, 200);
    return r;
  };
  window.addEventListener('popstate', () => setTimeout(checkPage, 200));

  new MutationObserver((mutations) => {
    // The widget animates and re-renders constantly; never let it trigger us.
    if (mutations.length && mutations.every(isWidgetMutation)) return;
    if (mutationTimer) clearTimeout(mutationTimer);
    mutationTimer = setTimeout(() => {
      mutationTimer = null;
      checkPage();
    }, 1500);
  }).observe(document.body, { childList: true, subtree: true, characterData: true });
}

function showChatNotice(text) {
  const msgContainer = document.getElementById('alc-chat-messages');
  if (!msgContainer) return;
  msgContainer.innerHTML = '';
  const notice = document.createElement('div');
  notice.className = 'alc-chat-notice';
  notice.textContent = text;
  msgContainer.appendChild(notice);
  chatInitialized = true;
}

function checkPage() {
  const urlChanged = location.href !== lastUrl;
  if (urlChanged) lastUrl = location.href;

  const fingerprint = questionFingerprint();
  const questionChanged = !!fingerprint && fingerprint !== lastQuestionSignature;
  if (questionChanged) lastQuestionSignature = fingerprint;

  // Ordinary page churn is not a reason to throw away the conversation.
  if (!urlChanged && !questionChanged) return;

  const input = document.getElementById('alc-chat-input');
  if (input && document.activeElement === input && input.value.trim()) return;

  chatHistory = [];
  chatInitialized = false;
  const chatInput = document.getElementById('alc-chat-input');
  if (chatInput) chatInput.value = '';

  showChatNotice(
    urlChanged
      ? 'New page detected — ask about this question.'
      : 'New question detected — chat reset.'
  );
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

function captureBannerHtml(ctx, forceExpanded) {
  if (!ctx) return '';
  const label = ctx.label || ctx.source || 'page';
  let html = `<div class="alc-capture">Using: <strong>${escapeHtml(label)}</strong></div>`;

  if (forceExpanded || previewCapture) {
    const bits = [];
    if (ctx.question_text) bits.push(`Question / selection:\n${ctx.question_text}`);
    if (ctx.options && ctx.options.length) {
      bits.push(`Options:\n${ctx.options.map((o, i) => `${String.fromCharCode(65 + i)}. ${o}`).join('\n')}`);
    }
    if (ctx.context_text) bits.push(`Context:\n${ctx.context_text}`);
    html += `<pre class="alc-capture-preview">${escapeHtml(bits.join('\n\n') || '(nothing captured)')}</pre>`;
  }
  return html;
}

function showCapturePreview() {
  const ctx = getQuestionContext();
  lastCapture = ctx;
  showResult(captureBannerHtml(ctx, true));
}

async function doAction(action) {
  const ctx = getQuestionContext();
  lastCapture = ctx;
  // Code blocks are only useful for coding help; sending them with an MCQ or
  // an explanation just burns context and confuses the model.
  const codeContext = action === 'coding-help' ? getCodeBlocks() : '';

  showLoading();

  try {
    const res = await fetch(`${API_BASE}/api/extension/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action,
        text: ctx.question_text,
        options: ctx.options && ctx.options.length ? ctx.options : undefined,
        context: ctx.context_text,
        title: ctx.page_title,
        code_context: codeContext || undefined,
      }),
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Request failed');
    const data = await res.json();
    renderResult(action, data, ctx);
  } catch (e) {
    const msg = e.message.includes('fetch') ? 'Cannot reach backend. Is it running on localhost:8000?' : e.message;
    showError(msg);
  }
}

function renderResult(action, data, ctx) {
  if (data.error) { showError(data.error); return; }

  let html = captureBannerHtml(ctx);

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

  const pageContext = getPageText().slice(0, MAX_PAGE_CHARS);
  const codeIntent = /\b(code|write|implement|solve|solution|function|program|snippet|fix|syntax)\b/i.test(text);
  const codeContext = codeIntent ? getCodeBlocks() : '';

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
