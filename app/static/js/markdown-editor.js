/**
 * markdown-editor.js - Markdown workspace logic, Split/Overlay layout modes, auto-save, and formatting
 */

let mdEditorMode = localStorage.getItem('mininotebook_md_mode') || localStorage.getItem('scholar_md_mode') || 'edit';
let mdLayoutMode = localStorage.getItem('mininotebook_md_layout_mode') || localStorage.getItem('scholar_md_layout_mode') || 'split';
let mdSaveTimer = null;
let mdLayoutAnimation = null;
let mdPanelPlaceholder = null;

function initMarkdownEditor() {
  const textarea = document.getElementById('md-textarea');
  const titleInput = document.getElementById('md-doc-title');
  if (!textarea) return;

  const savedContent = localStorage.getItem('mininotebook_markdown_content') || localStorage.getItem('scholar_markdown_content');
  if (savedContent !== null) {
    textarea.value = savedContent;
  } else {
    textarea.value = '# Ghi chú nghiên cứu\n\n' +
      'Chào mừng bạn đến với khu vực **soạn thảo Markdown**!\n\n' +
      '- Bạn có thể tự do ghi lại ý tưởng, phân tích tài liệu và cấu trúc bài báo.\n' +
      '- Bấm nút **"Chèn vào Markdown"** dưới câu trả lời của AI bên cạnh để tự động thêm vào đây.\n' +
      '- Có thể đặt ghi chú cạnh khung chat hoặc phủ toàn bộ khung chat bằng hai nút ở thanh tiêu đề.\n\n---\n';
  }

  const savedTitle = localStorage.getItem('mininotebook_markdown_title') || localStorage.getItem('scholar_markdown_title');
  if (savedTitle && titleInput) {
    titleInput.value = savedTitle;
  }

  setEditorViewMode(mdEditorMode);
  setMarkdownLayoutMode(mdLayoutMode);
  updateMarkdownStats();
  updateMarkdownPreview();

  textarea.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      textarea.value = textarea.value.substring(0, start) + '  ' + textarea.value.substring(end);
      textarea.selectionStart = textarea.selectionEnd = start + 2;
      handleMarkdownInput();
      return;
    }

    if ((e.ctrlKey || e.metaKey) && (e.key === 'b' || e.key === 'B')) {
      e.preventDefault();
      insertMd('**', '**', 'chữ in đậm');
      return;
    }

    // Ctrl + I: Toggle Settings (per user specification)
    if ((e.ctrlKey || e.metaKey) && (e.key === 'i' || e.key === 'I')) {
      e.preventDefault();
      if (typeof toggleSettingsModal === 'function') {
        toggleSettingsModal();
      }
      return;
    }

    // Ctrl + M: Toggle Markdown panel
    if ((e.ctrlKey || e.metaKey) && !e.shiftKey && (e.key === 'm' || e.key === 'M')) {
      e.preventDefault();
      if (typeof toggleMarkdownPanel === 'function') {
        toggleMarkdownPanel();
      }
      return;
    }

    // Ctrl + Shift + S: Toggle Sources panel
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 's' || e.key === 'S')) {
      e.preventDefault();
      if (typeof toggleSourcesSidebar === 'function') {
        toggleSourcesSidebar();
      }
      return;
    }
  });

  initMarkdownLayoutTracking();
}

function handleMarkdownInput() {
  const textarea = document.getElementById('md-textarea');
  if (!textarea) return;
  const text = textarea.value;

  const ind = document.getElementById('md-save-indicator');
  if (ind) ind.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span> ${t('Đang lưu...')}`;

  if (mdSaveTimer) clearTimeout(mdSaveTimer);
  mdSaveTimer = setTimeout(() => {
    try {
      localStorage.setItem('mininotebook_markdown_content', text);
      localStorage.setItem('scholar_markdown_content', text);
    } catch (e) {}
    if (ind) ind.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> ${t('Đã lưu')}`;
  }, 300);

  updateMarkdownStats();
  if (mdEditorMode === 'split' || mdEditorMode === 'preview') {
    updateMarkdownPreview();
  }
}

function updateMarkdownStats() {
  const textarea = document.getElementById('md-textarea');
  if (!textarea) return;
  const text = textarea.value.trim();

  const words = text ? text.split(/\s+/).filter(Boolean).length : 0;
  const chars = text.length;
  const lines = text ? text.split('\n').length : 1;

  const wordsEl = document.getElementById('md-stat-words');
  const charsEl = document.getElementById('md-stat-chars');
  const linesEl = document.getElementById('md-stat-lines');

  if (wordsEl) wordsEl.textContent = `${words} ${t('từ')}`;
  if (charsEl) charsEl.textContent = `${chars} ${t('ký tự')}`;
  if (linesEl) linesEl.textContent = `${lines} ${t('dòng')}`;
}

function updateMarkdownPreview() {
  const preview = document.getElementById('md-preview-pane');
  const textarea = document.getElementById('md-textarea');
  if (!preview || !textarea) return;

  const raw = textarea.value;
  if (!raw.trim()) {
    preview.innerHTML = '<div class="text-xs t-faint italic p-4 text-center">Nội dung xem trước sẽ hiển thị ở đây...</div>';
    return;
  }

  try {
    preview.innerHTML = renderMarkdown(raw);
  } catch (err) {
    preview.innerHTML = '<div class="text-xs text-red-400 p-2">Lỗi render: ' + escapeHtml(err.message) + '</div>';
  }
}

function setEditorViewMode(mode) {
  mdEditorMode = mode;
  try {
    localStorage.setItem('mininotebook_md_mode', mode);
    localStorage.setItem('scholar_md_mode', mode);
  } catch (e) {}

  const editorPane = document.getElementById('md-editor-pane');
  const previewPane = document.getElementById('md-preview-pane');
  const btnEdit = document.getElementById('btn-md-mode-edit');
  const btnSplit = document.getElementById('btn-md-mode-split');
  const btnPreview = document.getElementById('btn-md-mode-preview');

  [btnEdit, btnSplit, btnPreview].forEach(b => { if (b) b.classList.remove('active'); });

  if (mode === 'preview') {
    if (editorPane) editorPane.classList.add('hidden');
    if (previewPane) {
      previewPane.classList.remove('hidden');
      previewPane.style.width = '100%';
    }
    if (btnPreview) btnPreview.classList.add('active');
    updateMarkdownPreview();
  } else if (mode === 'split') {
    if (editorPane) {
      editorPane.classList.remove('hidden');
      editorPane.style.width = '50%';
    }
    if (previewPane) {
      previewPane.classList.remove('hidden');
      previewPane.style.width = '50%';
    }
    if (btnSplit) btnSplit.classList.add('active');
    updateMarkdownPreview();
  } else {
    if (editorPane) {
      editorPane.classList.remove('hidden');
      editorPane.style.width = '100%';
    }
    if (previewPane) previewPane.classList.add('hidden');
    if (btnEdit) btnEdit.classList.add('active');
  }
}

function setMarkdownLayoutMode(mode) {
  const panel = document.getElementById('markdown-panel');
  if (!panel) return;

  // Freeze/cancel any running FLIP animation before measuring a new start.
  if (mdLayoutAnimation) {
    const running = mdLayoutAnimation;
    mdLayoutAnimation = null;
    running.cancel();
  }
  panel.classList.remove('md-layout-animating');
  const before = panel.getBoundingClientRect();
  const wasVisible = getComputedStyle(panel).display !== 'none' && before.width > 0 && before.height > 0;

  mdLayoutMode = mode === 'overlay' ? 'overlay' : 'split';
  try {
    localStorage.setItem('mininotebook_md_layout_mode', mdLayoutMode);
    localStorage.setItem('scholar_md_layout_mode', mdLayoutMode);
  } catch (e) {}

  const splitBtn = document.getElementById('btn-md-layout-split');
  const overlayBtn = document.getElementById('btn-md-layout-overlay');
  [splitBtn, overlayBtn].forEach(btn => {
    if (!btn) return;
    const active = (btn === splitBtn && mdLayoutMode === 'split') || (btn === overlayBtn && mdLayoutMode === 'overlay');
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-pressed', active ? 'true' : 'false');
  });

  panel.classList.add('md-layout-animating');
  syncMarkdownPanelLayout();

  const after = panel.getBoundingClientRect();
  const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const isVisible = wasVisible && after.width > 0 && after.height > 0;
  if (!isVisible || reduceMotion || typeof panel.animate !== 'function') {
    panel.classList.remove('md-layout-animating');
    return;
  }

  const dx = before.left - after.left;
  const dy = before.top - after.top;
  const sx = before.width / after.width;
  const sy = before.height / after.height;
  const inverse = `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})`;
  const animation = panel.animate(
    [{ transform: inverse }, { transform: 'none' }],
    { duration: 480, easing: 'cubic-bezier(0.22, 1, 0.36, 1)' }
  );
  mdLayoutAnimation = animation;
  animation.onfinish = () => {
    if (mdLayoutAnimation !== animation) return;
    mdLayoutAnimation = null;
    panel.classList.remove('md-layout-animating');
  };
  animation.oncancel = () => {
    if (mdLayoutAnimation !== animation) return;
    mdLayoutAnimation = null;
    panel.classList.remove('md-layout-animating');
  };
}

function restoreMarkdownPanelToWorkspace(panel, chatMain) {
  if (mdPanelPlaceholder && mdPanelPlaceholder.parentNode) {
    mdPanelPlaceholder.parentNode.replaceChild(panel, mdPanelPlaceholder);
    mdPanelPlaceholder = null;
  } else if (chatMain && panel.parentElement === chatMain && chatMain.parentElement) {
    chatMain.parentElement.insertBefore(panel, chatMain.nextSibling);
  }
}

function syncMarkdownPanelLayout() {
  const panel = document.getElementById('markdown-panel');
  const chatMain = document.getElementById('chat-main-panel');
  if (!panel || !chatMain) return;

  const isHidden = getComputedStyle(panel).display === 'none' || panel.classList.contains('markdown-hidden');
  if (mdLayoutMode !== 'overlay' || isHidden) {
    panel.classList.remove('md-overlay-mode');
    restoreMarkdownPanelToWorkspace(panel, chatMain);
    ['left', 'top', 'width', 'height', 'z-index', 'right', 'bottom', 'inset'].forEach(prop => panel.style.removeProperty(prop));
    return;
  }

  if (panel.parentElement !== chatMain) {
    if (!mdPanelPlaceholder && panel.parentNode) {
      mdPanelPlaceholder = document.createComment('markdown-panel-original-slot');
      panel.parentNode.insertBefore(mdPanelPlaceholder, panel);
    }
    chatMain.appendChild(panel);
  }
  panel.classList.add('md-overlay-mode');
  ['left', 'top', 'width', 'height', 'right', 'bottom'].forEach(prop => panel.style.removeProperty(prop));
  panel.style.removeProperty('inset');
}

function saveMarkdownDocTitle(val) {
  const title = (val || '').trim() || 'Ghi chú nghiên cứu.md';
  try {
    localStorage.setItem('mininotebook_markdown_title', title);
    localStorage.setItem('scholar_markdown_title', title);
  } catch (e) {}
}

function insertMd(prefix, suffix, defaultText) {
  const textarea = document.getElementById('md-textarea');
  if (!textarea) return;

  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const selected = textarea.value.substring(start, end);
  const textToWrap = selected || defaultText || '';

  const replacement = prefix + textToWrap + suffix;
  textarea.value = textarea.value.substring(0, start) + replacement + textarea.value.substring(end);

  textarea.focus();
  textarea.selectionStart = start + prefix.length;
  textarea.selectionEnd = start + prefix.length + textToWrap.length;

  handleMarkdownInput();
}

function insertTableTemplate() {
  const tableTpl = '\n| Tiêu đề 1 | Tiêu đề 2 | Tiêu đề 3 |\n|:----------|:---------:|----------:|\n| Dữ liệu A | Dữ liệu B | Dữ liệu C |\n| Dữ liệu 1 | Dữ liệu 2 | Dữ liệu 3 |\n\n';
  insertMd('', '', tableTpl);
}

function insertChatAnswerToMarkdown(question, answerText) {
  const textarea = document.getElementById('md-textarea');
  if (!textarea) return;

  openMarkdownPanel();

  const divider = textarea.value.trim().length > 0 ? '\n\n---\n\n' : '';
  const formattedEntry = divider + '### ' + question + '\n\n' + answerText.trim() + '\n';

  textarea.value = textarea.value + formattedEntry;
  handleMarkdownInput();
  textarea.scrollTop = textarea.scrollHeight;
}

function openMarkdownPanel() {
  const panel = document.getElementById('markdown-panel');
  if (!panel) return;
  panel.classList.remove('markdown-hidden', 'hidden');
  panel.classList.add('flex');
  requestAnimationFrame(syncMarkdownPanelLayout);
}

function toggleMarkdownPanel() {
  const panel = document.getElementById('markdown-panel');
  if (!panel) return;
  const isHidden = getComputedStyle(panel).display === 'none';
  if (isHidden) {
    panel.classList.remove('markdown-hidden', 'hidden');
    panel.classList.add('flex');
    requestAnimationFrame(syncMarkdownPanelLayout);
  } else {
    if (mdLayoutAnimation) {
      const running = mdLayoutAnimation;
      mdLayoutAnimation = null;
      running.cancel();
    }
    panel.classList.remove('md-layout-animating', 'md-overlay-mode');
    restoreMarkdownPanelToWorkspace(panel, document.getElementById('chat-main-panel'));
    panel.classList.add('markdown-hidden', 'hidden');
    panel.classList.remove('flex');
    ['left', 'top', 'width', 'height', 'z-index', 'right', 'bottom', 'inset'].forEach(prop => panel.style.removeProperty(prop));
  }
}

function copyMarkdownContent() {
  const textarea = document.getElementById('md-textarea');
  if (!textarea) return;
  navigator.clipboard.writeText(textarea.value).then(() => {
    const ind = document.getElementById('md-save-indicator');
    if (ind) {
      const prev = ind.innerHTML;
      const copiedText = t('✓ Đã chép Markdown');
      ind.innerHTML = `<span class="text-sky-400 font-semibold">${copiedText}</span>`;
      setTimeout(() => { ind.innerHTML = prev; }, 1800);
    }
  });
}

function downloadMarkdownFile() {
  const textarea = document.getElementById('md-textarea');
  const titleInput = document.getElementById('md-doc-title');
  if (!textarea) return;

  let filename = (titleInput ? titleInput.value.trim() : '') || 'Ghi chú nghiên cứu.md';
  if (!filename.endsWith('.md')) filename += '.md';

  const blob = new Blob([textarea.value], { type: 'text/markdown;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function clearMarkdownContent() {
  if (confirm(t('Bạn có chắc muốn xóa toàn bộ nội dung trong bản ghi chú này?'))) {
    const textarea = document.getElementById('md-textarea');
    if (textarea) {
      textarea.value = '';
      handleMarkdownInput();
      textarea.focus();
    }
  }
}

function initMarkdownLayoutTracking() {
  const chatMain = document.getElementById('chat-main-panel');
  if (chatMain && 'ResizeObserver' in window) {
    const observer = new ResizeObserver(() => syncMarkdownPanelLayout());
    observer.observe(chatMain);
  }
  window.addEventListener('resize', () => requestAnimationFrame(syncMarkdownPanelLayout));
  document.addEventListener('scroll', () => {
    if (mdLayoutMode === 'overlay') syncMarkdownPanelLayout();
  }, true);
}

// Bind to window for global inline event handlers in HTML
window.initMarkdownEditor = initMarkdownEditor;
window.handleMarkdownInput = handleMarkdownInput;
window.updateMarkdownStats = updateMarkdownStats;
window.updateMarkdownPreview = updateMarkdownPreview;
window.setEditorViewMode = setEditorViewMode;
window.setMarkdownLayoutMode = setMarkdownLayoutMode;
window.syncMarkdownPanelLayout = syncMarkdownPanelLayout;
window.saveMarkdownDocTitle = saveMarkdownDocTitle;
window.insertMd = insertMd;
window.insertTableTemplate = insertTableTemplate;
window.insertChatAnswerToMarkdown = insertChatAnswerToMarkdown;
window.openMarkdownPanel = openMarkdownPanel;
window.toggleMarkdownPanel = toggleMarkdownPanel;
window.toggleStudio = toggleMarkdownPanel;
window.copyMarkdownContent = copyMarkdownContent;
window.downloadMarkdownFile = downloadMarkdownFile;
window.clearMarkdownContent = clearMarkdownContent;
window.initMarkdownLayoutTracking = initMarkdownLayoutTracking;
