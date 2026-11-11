/**
 * sources.js - Sources list rendering, ArXiv ingest, PDF upload, inspection drawer, and deletion
 */

function renderSourcesList() {
  const container = document.getElementById('sources-list-container');
  if (!container) return;
  const kw = (document.getElementById('paper-filter').value || '').toLowerCase();
  const papers = (window.globalState && window.globalState.papers) || [];
  const filtered = papers.filter(p =>
    !kw || p.title.toLowerCase().includes(kw) || p.paper_id.toLowerCase().includes(kw) || p.authors.join(' ').toLowerCase().includes(kw)
  );

  const isEn = window.currentLanguage === 'en';
  if (!filtered.length) {
    const emptyMsg = papers.length
      ? t('Không có nguồn nào khớp bộ lọc.')
      : t('Các nguồn đã lưu sẽ hiển thị ở đây.<br>Thêm bài báo để bắt đầu.');
    const addFirst = papers.length
      ? ''
      : `<button onclick="openAddSourceModal()" class="text-xs t-accent hover:underline">${t('+ Thêm nguồn đầu tiên')}</button>`;

    container.innerHTML = `
      <div class="p-8 text-center space-y-3">
        <div class="text-3xl">📄</div>
        <div class="text-xs t-muted leading-relaxed">${emptyMsg}</div>
        ${addFirst}
      </div>`;
    return;
  }

  const chunkUnit = t('đoạn');
  const delLabel = t('Xóa nguồn');

  container.innerHTML = filtered.map(p => `
    <div onclick="inspectSourcePaper('${escapeAttr(p.paper_id)}')" class="src-row">
      <div class="src-icon">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8l-5-5zM14 3v5h5"/></svg>
      </div>
      <div class="min-w-0 flex-1">
        <div class="src-title-tooltip text-[13px] t-strong leading-snug line-clamp-2" data-tooltip="${escapeHtml(p.title)}" tabindex="0">${escapeHtml(p.title)}</div>
        <div class="text-[11px] t-faint font-mono mt-0.5 truncate">${escapeHtml(p.paper_id)} • ${p.chunk_count} ${chunkUnit}</div>
      </div>
      <button onclick="event.stopPropagation(); deletePaper('${escapeAttr(p.paper_id)}')" aria-label="${delLabel}" data-tooltip="${delLabel}" class="src-del icon-btn sm shrink-0 hover:!text-[color:var(--danger)]">✕</button>
    </div>
  `).join('');
}

function inspectSourcePaper(paperId) {
  const papers = (window.globalState && window.globalState.papers) || [];
  const p = papers.find(x => x.paper_id === paperId);
  if (!p) return;
  const isEn = window.currentLanguage === 'en';
  const isArxiv = /^\d{4}\.\d{4,5}$/.test(p.paper_id);
  const linksHtml = isArxiv
    ? `<div class="flex gap-2 pt-1">
         <a href="https://arxiv.org/abs/${p.paper_id}" target="_blank" class="btn-outline !py-1.5 !text-xs">ArXiv ↗</a>
         <a href="https://arxiv.org/pdf/${p.paper_id}.pdf" target="_blank" class="btn-outline !py-1.5 !text-xs">PDF ↗</a>
       </div>` : '';
  const sectionsHtml = (p.sections || []).map(s => `<span class="chip font-mono !text-[11px] mr-1.5 mb-1.5">${escapeHtml(s)}</span>`).join('');
  const structTitle = `${t('Cấu trúc tài liệu')} (${(p.sections || []).length} ${t('mục')})`;

  openDrawer(`${t('Hướng dẫn nguồn')} • ${p.paper_id}`, `
    <div class="space-y-3">
      <h3 class="text-base font-medium t-strong leading-snug">${escapeHtml(p.title)}</h3>
      <div class="t-muted">${escapeHtml((p.authors || []).join(', ') || t('Không rõ tác giả'))}</div>
      <div class="flex flex-wrap gap-x-3 gap-y-1 text-[11px] font-mono t-faint">
        <span>${t('Xuất bản:')} ${escapeHtml(p.published_date || '')}</span><span>•</span>
        <span>${t('Trích dẫn:')} ${p.citation_count ?? 0}</span><span>•</span>
        <span>${t('Chunks:')} ${p.chunk_count ?? 0}</span>
      </div>
      ${linksHtml}
    </div>
    ${p.abstract ? `
      <div class="surface p-4 space-y-1.5">
        <div class="text-[11px] font-semibold uppercase tracking-wider t-muted">${t('Tóm tắt')}</div>
        <p class="t-strong leading-relaxed" style="color: var(--text)">${escapeHtml(p.abstract)}</p>
      </div>` : ''}
    <div class="space-y-2">
      <div class="text-[11px] font-semibold uppercase tracking-wider t-muted">${structTitle}</div>
      <div>${sectionsHtml}</div>
    </div>
  `);
}

async function ingestFromArxiv() {
  const query = document.getElementById('arxiv-query').value.trim();
  const maxPapers = parseInt(document.getElementById('arxiv-max').value || '2', 10);
  const msg = document.getElementById('ingest-msg');
  const btn = document.getElementById('btn-do-ingest');
  if (!query) return;

  btn.disabled = true;
  btn.textContent = t('Đang tải & phân tích PDF...');
  msg.className = 'mt-4 text-xs font-mono rounded-xl px-4 py-3 surface t-muted';
  msg.style.color = '';
  msg.textContent = window.currentLanguage === 'en'
    ? `Searching for '${query}' on ArXiv & OpenAlex...`
    : `Đang tìm '${query}' trên ArXiv & OpenAlex...`;

  try {
    const data = await Api.ingestArxiv(query, maxPapers);
    msg.className = 'mt-4 text-xs font-mono rounded-xl px-4 py-3 surface';
    msg.style.color = 'var(--ok)';
    msg.textContent = window.currentLanguage === 'en'
      ? `✓ Added ${data.papers_ingested} papers (${data.chunks_indexed} chunks)`
      : `✓ Đã thêm ${data.papers_ingested} bài (${data.chunks_indexed} phân đoạn)`;
    await loadStats();
    setTimeout(() => closeAddSourceModal(), 900);
  } catch (err) {
    msg.className = 'mt-4 text-xs font-mono rounded-xl px-4 py-3 surface';
    msg.style.color = 'var(--danger)';
    let errText = err.message;
    if (err.message === 'Failed to fetch') {
      if (window.location.protocol === 'file:') {
        errText = 'Trang web đang mở qua file://. Vui lòng mở trình duyệt tại: http://localhost:8000';
      } else {
        errText = t('Không thể kết nối đến server. Vui lòng kiểm tra terminal chạy server!');
      }
    }
    msg.textContent = `${t('Lỗi')}: ${errText}`;
  } finally {
    btn.disabled = false;
    btn.textContent = t('Tải & lập chỉ mục');
  }
}

async function uploadLocalPdf() {
  const fileInput = document.getElementById('pdf-file');
  const titleInput = document.getElementById('pdf-title');
  const msg = document.getElementById('ingest-msg');
  const btn = document.getElementById('btn-do-upload');
  if (!fileInput.files.length) return;

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  if (titleInput.value.trim()) formData.append('title', titleInput.value.trim());

  btn.disabled = true;
  btn.textContent = t('Đang phân tích PDF...');
  msg.className = 'mt-4 text-xs font-mono rounded-xl px-4 py-3 surface t-muted';
  msg.style.color = '';
  msg.textContent = t('Đang chạy layout parser & RapidOCR...');

  try {
    const data = await Api.uploadPdf(formData);
    msg.className = 'mt-4 text-xs font-mono rounded-xl px-4 py-3 surface';
    msg.style.color = 'var(--ok)';
    msg.textContent = window.currentLanguage === 'en'
      ? `✓ Added '${data.title}' (${data.chunks_indexed} chunks)`
      : `✓ Đã thêm '${data.title}' (${data.chunks_indexed} phân đoạn)`;
    fileInput.value = '';
    titleInput.value = '';
    await loadStats();
    setTimeout(() => closeAddSourceModal(), 900);
  } catch (err) {
    msg.className = 'mt-4 text-xs font-mono rounded-xl px-4 py-3 surface';
    msg.style.color = 'var(--danger)';
    let errText = err.message;
    if (err.message === 'Failed to fetch') {
      if (window.location.protocol === 'file:') {
        errText = 'Trang web đang mở qua file://. Vui lòng mở trình duyệt tại: http://localhost:8000';
      } else {
        errText = t('Không thể kết nối đến server. Vui lòng kiểm tra terminal chạy server!');
      }
    }
    msg.textContent = `${t('Lỗi')}: ${errText}`;
  } finally {
    btn.disabled = false;
    btn.textContent = t('Phân tích bằng RapidOCR & lập chỉ mục');
  }
}

async function deletePaper(paperId) {
  try {
    await Api.deletePaper(paperId);
  } catch (e) {
    console.error('Lỗi khi xóa bài báo:', e);
  }
  await loadStats();
}

window.renderSourcesList = renderSourcesList;
window.inspectSourcePaper = inspectSourcePaper;
window.ingestFromArxiv = ingestFromArxiv;
window.uploadLocalPdf = uploadLocalPdf;
window.deletePaper = deletePaper;
