/**
 * main.js - Application bootstrap, metrics loading, suggestions, and initialization
 */

async function loadStats() {
  if (window.location.protocol === 'file:') {
    alert('⚠️ Chú ý: Bạn đang mở trang web trực tiếp từ ổ đĩa (địa chỉ file://).\nTrình duyệt sẽ chặn kết nối tới server và không thể tải bài báo hay ingest được.\n\n👉 Vui lòng mở trình duyệt và gõ địa chỉ: http://localhost:8000');
    return;
  }
  let data;
  try {
    data = await Api.getStats();
  } catch (err) {
    console.error('Không thể kết nối đến server /api/stats:', err);
    return;
  }
  window.globalState.papers = data.papers || [];

  const n = data.metrics.ingested_papers;
  const statPapers = document.getElementById('stat-papers');
  const inputSourceBadge = document.getElementById('input-source-badge');
  const overviewSub = document.getElementById('overview-sub');
  const statChunks = document.getElementById('stat-chunks');
  const statNodes = document.getElementById('stat-nodes');
  const statEdges = document.getElementById('stat-edges');

  const isEn = window.currentLanguage === 'en';
  const sourceLabel = isEn ? 'sources' : 'nguồn';
  const chunkLabel = isEn ? 'chunks' : 'phân đoạn';

  if (statPapers) statPapers.textContent = n;
  if (inputSourceBadge) inputSourceBadge.textContent = `${n} ${sourceLabel}`;
  if (overviewSub) overviewSub.textContent = `${n} ${sourceLabel} • ${data.metrics.indexed_chunks} ${chunkLabel}`;
  if (statChunks) statChunks.textContent = data.metrics.indexed_chunks;
  if (statNodes) statNodes.textContent = data.metrics.total_nodes;
  if (statEdges) statEdges.textContent = data.metrics.total_citation_edges;

  const cfgProvider = document.getElementById('cfg-provider');
  const cfgModel = document.getElementById('cfg-model');
  const cfgBaseUrl = document.getElementById('cfg-base-url');
  const cfgReasoning = document.getElementById('cfg-reasoning');

  if (cfgProvider) cfgProvider.value = data.config.llm_provider || 'gemini';
  if (cfgModel) cfgModel.value = data.config.llm_model || 'gemini-2.5-flash';
  if (cfgBaseUrl) cfgBaseUrl.value = data.config.llm_base_url || '';
  if (cfgReasoning) cfgReasoning.value = data.config.llm_reasoning_effort || 'medium';

  renderSettingsControls();
  setLanguage(localStorage.getItem('scholar_lang') || data.config.llm_language || 'vi');
  onProviderChange();

  const badge = document.getElementById('llm-status-badge');
  const dot = document.getElementById('llm-dot');
  if (badge && dot) {
    if (data.config.llm_configured) {
      dot.style.background = 'var(--ok)';
      dot.style.boxShadow = '0 0 8px var(--ok)';
      badge.textContent = data.config.llm_model;
    } else {
      dot.style.background = 'var(--warn)';
      dot.style.boxShadow = 'none';
      badge.textContent = 'Extractive Mode';
    }
  }

  const sugBox = document.getElementById('suggestions-box');
  if (sugBox) {
    sugBox.innerHTML = '';
    (data.suggestions || []).forEach(s => {
      const btn = document.createElement('button');
      btn.className = 'text-xs px-4 py-2.5 rounded-2xl text-left transition max-w-full';
      btn.style.cssText = 'background: var(--surface); color: var(--text); border: 1px solid var(--border);';
      btn.onmouseenter = () => { btn.style.background = 'var(--surface-hover)'; };
      btn.onmouseleave = () => { btn.style.background = 'var(--surface)'; };
      btn.textContent = s.label;
      btn.onclick = () => {
        const input = document.getElementById('question-input');
        if (input) {
          input.value = s.question;
          input.focus();
        }
      };
      sugBox.appendChild(btn);
    });
  }

  renderSourcesList();
}

window.loadStats = loadStats;

// Bootstrap on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
  const savedTitle = (function () {
    try { return localStorage.getItem('scholar_title'); } catch (e) { return null; }
  })();
  saveNotebookTitle(savedTitle || 'Sổ tay nghiên cứu');
  document.title = 'MiniNotebook';
  applyTheme(document.documentElement.getAttribute('data-theme') || 'dark');
  switchIngestTab('arxiv');
  initDropZone();
  initCustomSelects();
  setLanguage(window.currentLanguage);
  initMarkdownEditor();
  if (typeof initI18nObserver === 'function') initI18nObserver();
  if (typeof initSourceTooltips === 'function') initSourceTooltips();
  loadStats();
});
