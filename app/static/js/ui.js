/**
 * ui.js - Modal dialogs, drawer, tabs, custom select dropdowns, tooltips, and UI helpers
 */

/* ================= ESCAPE HELPERS ================= */
function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, ch => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[ch]));
}

function escapeAttr(s) {
  return String(s ?? '').replace(/["']/g, ch => ({ '"': '&quot;', "'": '&#39;' }[ch]));
}

function fmtMs(ms) {
  return ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(1)}s`;
}

/* ================= PANELS / MODALS ================= */
function openAddSourceModal() {
  const msg = document.getElementById('ingest-msg');
  if (msg) msg.classList.add('hidden');
  const modal = document.getElementById('modal-add-source');
  if (modal) modal.classList.remove('hidden');
  setTimeout(() => {
    const q = document.getElementById('arxiv-query');
    if (q && window.currentIngestTab === 'arxiv') q.focus();
  }, 50);
}

function closeAddSourceModal() {
  const modal = document.getElementById('modal-add-source');
  if (modal) modal.classList.add('hidden');
}

function openSettingsModal() {
  const modal = document.getElementById('modal-settings');
  if (modal) modal.classList.remove('hidden');
  onProviderChange();
  renderSettingsControls();
}

function closeSettingsModal() {
  const modal = document.getElementById('modal-settings');
  if (modal) modal.classList.add('hidden');
}

function toggleSettingsModal() {
  const modal = document.getElementById('modal-settings');
  if (!modal) return;
  if (modal.classList.contains('hidden')) {
    openSettingsModal();
  } else {
    closeSettingsModal();
  }
}

function closeSourceDrawer() {
  const drawer = document.getElementById('source-drawer');
  if (drawer) drawer.classList.add('hidden');
}

function openDrawer(badge, html) {
  const badgeEl = document.getElementById('drawer-badge');
  const bodyEl = document.getElementById('drawer-body');
  const drawer = document.getElementById('source-drawer');
  if (badgeEl) badgeEl.textContent = badge;
  if (bodyEl) bodyEl.innerHTML = html;
  if (drawer) drawer.classList.remove('hidden');
}

function saveNotebookTitle(v) {
  const title = (v || '').trim() || 'Sổ tay nghiên cứu';
  try {
    localStorage.setItem('mininotebook_title', title);
    localStorage.setItem('scholar_title', title);
  } catch (e) {}
  const overviewTitle = document.getElementById('overview-title');
  if (overviewTitle) overviewTitle.textContent = title;
  document.title = 'MiniNotebook';
}

function toggleSourcesSidebar() {
  const sidebar = document.getElementById('sources-sidebar');
  if (!sidebar) return;
  const hidden = sidebar.classList.toggle('hidden');
  const btn = document.getElementById('btn-open-sources');
  if (btn) btn.classList.toggle('hidden', !hidden);
}

/* ================= INGEST TABS ================= */
function styleIngestTabs(tab) {
  const a = document.getElementById('btn-ingest-arxiv');
  const p = document.getElementById('btn-ingest-pdf');
  if (!a || !p) return;
  a.classList.toggle('active', tab === 'arxiv');
  p.classList.toggle('active', tab === 'pdf');
}

function switchIngestTab(tab) {
  window.currentIngestTab = tab;
  const pArxiv = document.getElementById('panel-ingest-arxiv');
  const pPdf = document.getElementById('panel-ingest-pdf');
  if (pArxiv) pArxiv.classList.toggle('hidden', tab !== 'arxiv');
  if (pPdf) pPdf.classList.toggle('hidden', tab !== 'pdf');
  styleIngestTabs(tab);
}

/* ================= KEYBOARD SHORTCUTS ================= */
window.addEventListener('keydown', (e) => {
  const isCtrl = e.ctrlKey || e.metaKey;
  const key = (e.key || '').toLowerCase();

  // 1. Ctrl + M: Đóng/mở ghi chú Markdown (ngăn chặn hành vi mặc định của trình duyệt)
  if (isCtrl && !e.shiftKey && !e.altKey && key === 'm') {
    e.preventDefault();
    if (typeof toggleMarkdownPanel === 'function') {
      toggleMarkdownPanel();
    }
    return;
  }

  // 2. Ctrl + Shift + S: Đóng/mở tab Source (ngăn chặn Web Capture / Save Page của trình duyệt)
  if (isCtrl && e.shiftKey && !e.altKey && key === 's') {
    e.preventDefault();
    if (typeof toggleSourcesSidebar === 'function') {
      toggleSourcesSidebar();
    }
    return;
  }

  // 3. Ctrl + I: Đóng/mở Settings (ngăn chặn Page Info / Italic mặc định của trình duyệt)
  if (isCtrl && !e.shiftKey && !e.altKey && key === 'i') {
    e.preventDefault();
    toggleSettingsModal();
    return;
  }

  // Escape: Đóng các modal, drawer hoặc custom select đang mở
  if (e.key === 'Escape' || e.key === 'Esc') {
    if (document.querySelector('.cs.open')) {
      document.querySelectorAll('.cs.open').forEach(x => x.classList.remove('open'));
      return;
    }
    closeAddSourceModal();
    closeSettingsModal();
    closeSourceDrawer();
  }
});

/* ================= SETTINGS CONTROLS ================= */
function onProviderChange() {
  const provEl = document.getElementById('cfg-provider');
  if (!provEl) return;
  const provider = provEl.value;
  const baseUrlInput = document.getElementById('cfg-base-url');
  const modelInput = document.getElementById('cfg-model');
  const isCustom = (provider === 'custom');
  if (baseUrlInput) {
    baseUrlInput.disabled = !isCustom;
    if (isCustom) {
      baseUrlInput.placeholder = 'VD: https://...trycloudflare.com/v1 hoặc http://localhost:8000/v1';
    } else {
      const defaultUrls = {
        gemini: 'Google Gemini Native API',
        openai: 'https://api.openai.com/v1',
        deepseek: 'https://api.deepseek.com/v1',
        groq: 'https://api.groq.com/openai/v1',
        openrouter: 'https://openrouter.ai/api/v1',
        ollama: 'http://localhost:11434/v1'
      };
      baseUrlInput.placeholder = `Mặc định (${defaultUrls[provider] || 'Official API'})`;
    }
  }
  const defaultModels = {
    gemini: 'gemini-2.5-flash',
    openai: 'gpt-4o-mini',
    deepseek: 'deepseek-chat',
    groq: 'llama-3.3-70b-versatile',
    openrouter: 'deepseek/deepseek-r1',
    ollama: 'qwen2.5:7b'
  };
  if (!isCustom && defaultModels[provider] && modelInput) {
    modelInput.value = defaultModels[provider];
  }
}

function renderSettingsControls() {
  if (typeof syncCustomSelects === 'function') syncCustomSelects();
  const searchEl = document.getElementById('cfg-search-mode');
  const reasonEl = document.getElementById('cfg-reasoning');
  const langEl = document.getElementById('cfg-language');

  const mode = (searchEl && searchEl.value) || 'hybrid';
  const reason = (reasonEl && reasonEl.value) || 'medium';
  const lang = (langEl && langEl.value) || window.currentLanguage || 'vi';

  document.querySelectorAll('[data-retrieval]').forEach(el => el.classList.toggle('active', el.dataset.retrieval === mode));
  document.querySelectorAll('[data-reason]').forEach(el => el.classList.toggle('active', el.dataset.reason === reason));
  document.querySelectorAll('[data-langopt]').forEach(el => el.classList.toggle('active', el.dataset.langopt === lang));
  document.querySelectorAll('[data-themeopt]').forEach(el => el.classList.toggle('active', el.dataset.themeopt === (isDark() ? 'dark' : 'light')));
}

function setRetrieval(v) {
  const el = document.getElementById('cfg-search-mode');
  if (el) el.value = v;
  renderSettingsControls();
}

function setReasoning(v) {
  const el = document.getElementById('cfg-reasoning');
  if (el) el.value = v;
  renderSettingsControls();
}

function toggleApiKey() {
  const i = document.getElementById('cfg-api-key');
  if (i) i.type = i.type === 'password' ? 'text' : 'password';
}

function pickPreset(btn) {
  document.querySelectorAll('.topic-chip').forEach(b => b.classList.toggle('active', b === btn));
  const q = document.getElementById('arxiv-query');
  if (q && btn) {
    q.value = btn.dataset.q;
    q.focus();
  }
}

function stepPapers(d) {
  const i = document.getElementById('arxiv-max');
  if (i) {
    i.value = Math.max(1, Math.min(8, (parseInt(i.value || '2', 10) || 2) + d));
  }
}

function updateFileName() {
  const fileInput = document.getElementById('pdf-file');
  const f = fileInput && fileInput.files && fileInput.files[0];
  const tag = document.getElementById('pdf-file-name');
  if (!tag) return;
  if (f) {
    tag.textContent = '📄 ' + f.name;
    tag.classList.remove('hidden');
  } else {
    tag.classList.add('hidden');
  }
}

function initDropZone() {
  const zone = document.getElementById('drop-zone');
  if (!zone) return;
  ['dragenter', 'dragover'].forEach(ev => zone.addEventListener(ev, e => {
    e.preventDefault();
    zone.classList.add('dragover');
  }));
  ['dragleave', 'drop'].forEach(ev => zone.addEventListener(ev, e => {
    e.preventDefault();
    zone.classList.remove('dragover');
  }));
  zone.addEventListener('drop', e => {
    const f = e.dataTransfer.files && e.dataTransfer.files[0];
    if (!f || !f.name.toLowerCase().endsWith('.pdf')) return;
    const dt = new DataTransfer();
    dt.items.add(f);
    const fileInput = document.getElementById('pdf-file');
    if (fileInput) {
      fileInput.files = dt.files;
      updateFileName();
    }
  });
}

/* ================= CUSTOM SELECT ================= */
function initCustomSelects() {
  document.querySelectorAll('select.field-lg').forEach(sel => {
    if (sel._cs) return;
    const wrap = document.createElement('div');
    wrap.className = 'cs';
    sel.parentNode.insertBefore(wrap, sel);
    wrap.appendChild(sel);
    sel.style.display = 'none';

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'cs-btn';
    btn.innerHTML = `
      <span class="cs-label truncate"></span>
      <svg class="cs-chev" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd"/>
      </svg>`;
    wrap.appendChild(btn);

    const menu = document.createElement('div');
    menu.className = 'cs-menu';
    wrap.appendChild(menu);

    Array.from(sel.options).forEach(o => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'cs-opt';
      b.dataset.value = o.value;
      b.textContent = o.textContent;
      b.onclick = () => {
        sel.value = o.value;
        wrap.classList.remove('open');
        sel.dispatchEvent(new Event('change'));
        syncCustomSelects();
      };
      menu.appendChild(b);
    });

    btn.onclick = (e) => {
      e.stopPropagation();
      document.querySelectorAll('.cs.open').forEach(x => { if (x !== wrap) x.classList.remove('open'); });
      wrap.classList.toggle('open');
    };
    sel._cs = wrap;
  });
  syncCustomSelects();
}

function syncCustomSelects() {
  document.querySelectorAll('select.field-lg').forEach(sel => {
    const wrap = sel._cs;
    if (!wrap) return;
    const cur = sel.options[sel.selectedIndex];
    const label = wrap.querySelector('.cs-label');
    if (label) label.textContent = cur ? cur.textContent : '';
    wrap.querySelectorAll('.cs-opt').forEach(o => o.classList.toggle('selected', o.dataset.value === sel.value));
  });
}

document.addEventListener('click', () => {
  document.querySelectorAll('.cs.open').forEach(x => x.classList.remove('open'));
});

/* ================= TOOLTIPS ================= */
function initSourceTooltips() {
  let tooltip = document.querySelector('.app-tooltip');
  if (!tooltip) {
    tooltip = document.createElement('div');
    tooltip.className = 'app-tooltip';
    tooltip.setAttribute('role', 'tooltip');
    document.body.appendChild(tooltip);
  }

  const selector = '[data-tooltip]';
  let activeTarget = null;
  let showTimer = null;

  function collectTitles(root) {
    const nodes = [];
    if (root instanceof Element && root.matches('[title]')) nodes.push(root);
    if (root && root.querySelectorAll) nodes.push(...root.querySelectorAll('[title]'));
    nodes.forEach(el => {
      const title = el.getAttribute('title');
      if (title && !el.hasAttribute('data-tooltip')) el.setAttribute('data-tooltip', title);
      if (title) el.removeAttribute('title');
    });
  }

  collectTitles(document);

  new MutationObserver(records => records.forEach(record => {
    record.addedNodes.forEach(node => { if (node.nodeType === 1) collectTitles(node); });
    if (record.type === 'attributes' && record.target instanceof Element) collectTitles(record.target);
  })).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['title'] });

  function positionTooltip(event) {
    if (!activeTarget) return;
    const rect = activeTarget.getBoundingClientRect();
    const x = event && Number.isFinite(event.clientX) ? event.clientX : rect.left + rect.width / 2;
    const y = event && Number.isFinite(event.clientY) ? event.clientY : rect.top;
    tooltip.style.left = '0px';
    tooltip.style.top = '0px';
    const tr = tooltip.getBoundingClientRect();
    const margin = 10;
    let left = x + 12;
    if (left + tr.width > innerWidth - margin) left = x - tr.width - 12;
    left = Math.max(margin, Math.min(left, innerWidth - tr.width - margin));
    let top = y - tr.height - 12;
    if (top < margin) top = y + 18;
    top = Math.max(margin, Math.min(top, innerHeight - tr.height - margin));
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
  }

  function hideTooltip() {
    clearTimeout(showTimer);
    showTimer = null;
    activeTarget = null;
    tooltip.classList.remove('is-visible');
  }

  function scheduleTooltip(target, event) {
    const label = target && target.getAttribute('data-tooltip');
    if (!label) return;
    clearTimeout(showTimer);
    activeTarget = target;
    tooltip.textContent = label;
    showTimer = setTimeout(() => {
      if (!activeTarget || !activeTarget.isConnected) return;
      tooltip.classList.add('is-visible');
      positionTooltip(event);
    }, 550);
  }

  document.addEventListener('pointerover', event => {
    const target = event.target instanceof Element ? event.target.closest(selector) : null;
    if (target && target !== activeTarget) scheduleTooltip(target, event);
  });

  document.addEventListener('pointermove', event => {
    if (activeTarget && tooltip.classList.contains('is-visible')) positionTooltip(event);
  });

  document.addEventListener('pointerout', event => {
    const target = event.target instanceof Element ? event.target.closest(selector) : null;
    if (target && target === activeTarget && !(event.relatedTarget && target.contains(event.relatedTarget))) {
      hideTooltip();
    }
  });

  document.addEventListener('focusin', event => {
    const target = event.target instanceof Element ? event.target.closest(selector) : null;
    if (target) scheduleTooltip(target, null);
  });

  document.addEventListener('focusout', event => {
    const target = event.target instanceof Element ? event.target.closest(selector) : null;
    if (target && target === activeTarget) hideTooltip();
  });

  window.addEventListener('scroll', hideTooltip, true);
  window.addEventListener('blur', hideTooltip);
}

// Bind to window for global inline event handlers in HTML
window.escapeHtml = escapeHtml;
window.escapeAttr = escapeAttr;
window.fmtMs = fmtMs;
window.openAddSourceModal = openAddSourceModal;
window.closeAddSourceModal = closeAddSourceModal;
window.openSettingsModal = openSettingsModal;
window.closeSettingsModal = closeSettingsModal;
window.toggleSettingsModal = toggleSettingsModal;
window.closeSourceDrawer = closeSourceDrawer;
window.openDrawer = openDrawer;
window.saveNotebookTitle = saveNotebookTitle;
window.toggleSourcesSidebar = toggleSourcesSidebar;
window.styleIngestTabs = styleIngestTabs;
window.switchIngestTab = switchIngestTab;
window.onProviderChange = onProviderChange;
window.renderSettingsControls = renderSettingsControls;
window.setRetrieval = setRetrieval;
window.setReasoning = setReasoning;
window.toggleApiKey = toggleApiKey;
window.pickPreset = pickPreset;
window.stepPapers = stepPapers;
window.updateFileName = updateFileName;
window.initDropZone = initDropZone;
window.initCustomSelects = initCustomSelects;
window.syncCustomSelects = syncCustomSelects;
window.initSourceTooltips = initSourceTooltips;
