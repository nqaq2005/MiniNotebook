/**
 * chat.js - Question submission, streaming answer processing, citation chips, and markdown rendering
 */

function renderMarkdown(text) {
  const html = marked.parse(String(text ?? ''));
  return (window.DOMPurify ? DOMPurify.sanitize(html) : escapeHtml(html));
}

function setAskButtonMode(streaming) {
  const btn = document.getElementById('btn-ask');
  if (!btn) return;
  btn.disabled = false;
  btn.dataset.mode = streaming ? 'stop' : 'send';
  btn.title = streaming ? t('Dừng') : t('Gửi');
  btn.innerHTML = streaming
    ? `<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>`
    : `<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2.4" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M12 5l7 7-7 7"/></svg>`;
}

// [paper_id: Section, p.X] -> numbered NotebookLM-style citation chip (SEC-06: data attribute instead of inline onclick)
function formatInlineCitations(htmlStr) {
  const papers = (window.globalState && window.globalState.papers) || [];
  return htmlStr.replace(/\[([0-9]{4}\.[0-9]{4,5}|[A-Za-z0-9_.\-]+):\s*([^\]]+)\]/g, (match, pid, sec) => {
    const idx = papers.findIndex(p => p.paper_id === pid);
    const label = idx >= 0 ? String(idx + 1) : escapeHtml(pid);
    return `<span data-paper-id="${escapeAttr(pid)}" class="cite-chip cursor-pointer" title="${escapeHtml(pid)} • ${escapeHtml(sec)}">${label}</span>`;
  });
}

function clearConversation() {
  const results = document.getElementById('qa-results');
  if (results) results.innerHTML = '';
  const overview = document.getElementById('notebook-overview');
  if (overview) overview.classList.remove('hidden');
}

async function submitQuestion(e) {
  if (e) e.preventDefault();
  if (window.activeController) {
    window.activeController.abort();
    return;
  }

  const input = document.getElementById('question-input');
  const question = input.value.trim();
  if (!question) return;
  input.value = '';

  const payload = {
    question,
    language: window.currentLanguage || 'vi',
    search_mode: document.getElementById('cfg-search-mode').value,
    llm_provider: document.getElementById('cfg-provider').value,
    llm_model: document.getElementById('cfg-model').value,
    llm_base_url: document.getElementById('cfg-base-url').value,
    reasoning_effort: document.getElementById('cfg-reasoning').value,
    api_key: document.getElementById('cfg-api-key').value
  };

  const overview = document.getElementById('notebook-overview');
  if (overview) overview.classList.add('hidden');
  const view = createStreamingCard(question);
  window.activeController = new AbortController();
  setAskButtonMode(true);

  try {
    const res = await Api.askStream(payload, window.activeController.signal);
    if (!res.ok || !res.body) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let nl;
      while ((nl = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, nl).trim();
        buffer = buffer.slice(nl + 1);
        if (line) view.handle(JSON.parse(line));
      }
    }
    if (buffer.trim()) view.handle(JSON.parse(buffer.trim()));
  } catch (err) {
    if (err.name === 'AbortError') view.stopped();
    else view.handle({ type: 'error', message: err.message });
  } finally {
    view.finish();
    window.activeController = null;
    setAskButtonMode(false);
  }
}

function createStreamingCard(question) {
  const container = document.getElementById('qa-results');
  const card = document.createElement('div');
  card.className = 'flex flex-col gap-4';
  const searchingSourcesText = t('Đang tìm trong nguồn…');
  const reasoningText = t('Đang suy luận…');
  const searchingDetailText = t('Đang tìm trong nguồn (Hybrid + Cross-Encoder)…');

  card.innerHTML = `
    <div class="user-bubble">${escapeHtml(question)}</div>
    <div class="flex gap-3">
      <div class="w-7 h-7 rounded-full shrink-0 mt-0.5" style="background: conic-gradient(from 210deg, #4285f4, #9b72cb, #d96570, #4285f4);"></div>
      <div class="min-w-0 flex-1 space-y-3">
        <div class="flex items-center gap-2">
          <span data-role="badge" class="chip !py-0.5">${searchingSourcesText}</span>
        </div>
        <details data-role="thinking-wrap" class="hidden rounded-2xl px-4 py-2.5 surface">
          <summary class="text-xs font-medium t-accent cursor-pointer select-none"><span data-role="thinking-label">${reasoningText}</span></summary>
          <div data-role="thinking" class="mt-2 text-xs t-muted leading-relaxed whitespace-pre-wrap max-h-64 overflow-y-auto font-mono"></div>
        </details>
        <div data-role="notice" class="hidden text-xs rounded-xl px-3.5 py-2"></div>
        <div data-role="answer" class="markdown-body text-[14.5px]">
          <div class="flex items-center gap-2 text-xs t-muted">
            <span class="w-3.5 h-3.5 border-2 rounded-full animate-spin" style="border-color: var(--accent); border-top-color: transparent"></span>
            <span data-role="status">${searchingDetailText}</span>
          </div>
        </div>
        <div data-role="actions" class="hidden flex items-center gap-2 pt-1"></div>
        <details data-role="sources-wrap" class="w-full hidden">
          <summary data-role="sources-label" class="text-xs font-medium t-accent cursor-pointer select-none"></summary>
          <div data-role="sources" class="mt-3 grid grid-cols-1 gap-2.5"></div>
        </details>
        <div data-role="timings" class="text-[11px] font-mono t-faint"></div>
      </div>
    </div>
  `;
  container.appendChild(card);
  card.scrollIntoView({ behavior: 'smooth', block: 'end' });

  // SEC-06: Delegated click handler for citation chips and source cards (no inline onclick)
  card.addEventListener('click', (e) => {
    const target = e.target.closest('[data-paper-id]');
    if (target) {
      const pid = target.getAttribute('data-paper-id');
      if (pid && typeof inspectSourcePaper === 'function') {
        inspectSourcePaper(pid);
      }
    }
  });

  const $ = role => card.querySelector(`[data-role="${role}"]`);
  const scrollArea = document.getElementById('chat-scroll-area');
  let answerText = '';
  let thinkingText = '';
  let renderPending = false;
  let lastRenderTime = 0;
  let renderTimer = null;
  let gotFirstToken = false;
  let retrievalMs = null;
  let hadError = false;
  const tStart = performance.now();
  let tFirst = null;

  const nearBottom = () => scrollArea ? (scrollArea.scrollHeight - scrollArea.scrollTop - scrollArea.clientHeight < 160) : false;

  // PERF-05: Throttle markdown parsing & DOMPurify to max once every 75ms during streaming
  function scheduleRender(immediate = false) {
    if (renderPending && !immediate) return;
    const now = performance.now();
    const delay = immediate ? 0 : Math.max(0, 75 - (now - lastRenderTime));

    if (renderTimer) clearTimeout(renderTimer);
    renderPending = true;

    renderTimer = setTimeout(() => {
      requestAnimationFrame(() => {
        renderPending = false;
        lastRenderTime = performance.now();
        const stick = nearBottom();
        $('answer').innerHTML = formatInlineCitations(renderMarkdown(answerText)) +
          '<span class="inline-block w-1.5 h-4 align-middle animate-pulse ml-0.5" style="background: var(--accent)"></span>';
        if (thinkingText) $('thinking').textContent = thinkingText;
        if (stick && scrollArea) scrollArea.scrollTop = scrollArea.scrollHeight;
      });
    }, delay);
  }

  function setBadge(text, color) {
    const b = $('badge');
    b.textContent = text;
    b.style.color = color || '';
  }

  function markFirstToken() {
    if (gotFirstToken) return;
    gotFirstToken = true;
    tFirst = performance.now();
    setBadge(t('Đang tạo câu trả lời…'), 'var(--accent)');
  }

  function renderSources(citations) {
    $('sources-wrap').classList.remove('hidden');
    const isEn = window.currentLanguage === 'en';
    const count = citations.length;
    $('sources-label').textContent = isEn
      ? `View ${count} source ${count === 1 ? 'excerpt' : 'excerpts'}`
      : `Xem ${count} đoạn trích nguồn`;
    $('sources').innerHTML = citations.map((c, idx) => `
      <div data-paper-id="${escapeAttr(c.paper_id)}" class="surface p-3.5 space-y-1.5 cursor-pointer transition hover:opacity-90" style="border:1px solid var(--border)">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="text-xs font-medium t-accent font-mono">#${idx + 1} ${escapeHtml(c.citation_tag)}</span>
          <span class="text-[11px] t-faint font-mono">score: ${c.rerank_score}</span>
        </div>
        <div class="text-xs font-medium t-strong">${escapeHtml(c.paper_title)}</div>
        <div class="text-xs t-muted leading-relaxed line-clamp-3">${escapeHtml(c.content)}</div>
      </div>
    `).join('');
  }

  function renderActions() {
    if (!answerText || hadError) return;
    const actions = $('actions');
    actions.classList.remove('hidden');
    actions.innerHTML = `
      <button data-act="save" class="btn-outline !py-1.5 !text-xs flex items-center gap-1.5">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
        ${t('Chèn vào Markdown')}
      </button>
      <button data-act="copy" class="btn-outline !py-1.5 !text-xs">${t('Sao chép')}</button>`;
    actions.querySelector('[data-act="save"]').onclick = (ev) => {
      insertChatAnswerToMarkdown(question, answerText);
      ev.currentTarget.textContent = t('✓ Đã chèn');
    };
    actions.querySelector('[data-act="copy"]').onclick = async (ev) => {
      try {
        await navigator.clipboard.writeText(answerText);
        ev.currentTarget.textContent = t('✓ Đã chép');
      } catch (e) {}
    };
  }

  return {
    handle(ev) {
      switch (ev.type) {
        case 'status': {
          const s = $('status');
          if (s) s.textContent = ev.message;
          break;
        }
        case 'sources':
          retrievalMs = ev.retrieval_ms;
          renderSources(ev.citations || []);
          setBadge(t('Đang chờ token đầu tiên…'), 'var(--accent)');
          $('timings').textContent = `retrieval ${fmtMs(retrievalMs)}`;
          break;
        case 'thinking': {
          markFirstToken();
          thinkingText += ev.text;
          $('thinking-wrap').classList.remove('hidden');
          const isEn = window.currentLanguage === 'en';
          const count = thinkingText.length.toLocaleString();
          $('thinking-label').textContent = isEn
            ? `Reasoning… (${count} chars)`
            : `Đang suy luận… (${count} ký tự)`;
          if (!answerText) $('answer').innerHTML = `<div class="text-xs t-faint">${t('Mô hình đang suy luận — câu trả lời sẽ hiện ở đây…')}</div>`;
          scheduleRender();
          break;
        }
        case 'token':
          markFirstToken();
          answerText += ev.text;
          scheduleRender();
          break;
        case 'fallback': {
          answerText = ev.text || '';
          const n = $('notice');
          n.textContent = ev.message;
          n.className = 'text-xs rounded-xl px-3.5 py-2';
          n.style.cssText = 'background: color-mix(in srgb, var(--warn) 14%, transparent); color: var(--warn);';
          scheduleRender();
          break;
        }
        case 'done': {
          if (ev.answer) answerText = ev.answer;
          const t_metrics = ev.timings || {};
          const isGrounded = !!ev.is_grounded;
          const badgeText = isGrounded ? t('✓ Trích dẫn đã xác minh') : t('Đoạn trích nguồn');
          setBadge(badgeText, isGrounded ? 'var(--ok)' : 'var(--warn)');
          $('timings').textContent =
            `retrieval ${fmtMs(t_metrics.retrieval_ms)} • first token ${fmtMs(t_metrics.ttft_ms)} • generation ${fmtMs(t_metrics.llm_ms)} • total ${fmtMs(t_metrics.total_ms)}`;
          break;
        }
        case 'error': {
          hadError = true;
          const n = $('notice');
          n.textContent = `${t('Lỗi')}: ${ev.message}`;
          n.className = 'text-xs rounded-xl px-3.5 py-2';
          n.style.cssText = 'background: color-mix(in srgb, var(--danger) 14%, transparent); color: var(--danger);';
          setBadge(t('Lỗi'), 'var(--danger)');
          break;
        }
      }
    },
    stopped() {
      setBadge(t('Đã dừng'), 'var(--muted)');
      const elapsed = Math.round(performance.now() - tStart);
      const stoppedLabel = t('đã dừng sau');
      $('timings').textContent = `${stoppedLabel} ${fmtMs(elapsed)}` + (tFirst ? ` • first token ${fmtMs(Math.round(tFirst - tStart))}` : '');
    },
    finish() {
      $('answer').innerHTML = answerText
        ? formatInlineCitations(renderMarkdown(answerText))
        : `<div class="text-xs t-faint">${t('Chưa có câu trả lời.')}</div>`;
      if (thinkingText) {
        const isEn = window.currentLanguage === 'en';
        const count = thinkingText.length.toLocaleString();
        $('thinking').textContent = thinkingText;
        $('thinking-label').textContent = isEn
          ? `Reasoning process (${count} chars)`
          : `Quá trình suy luận (${count} ký tự)`;
      }
      renderActions();
    }
  };
}

window.renderMarkdown = renderMarkdown;
window.setAskButtonMode = setAskButtonMode;
window.formatInlineCitations = formatInlineCitations;
window.clearConversation = clearConversation;
window.submitQuestion = submitQuestion;
window.createStreamingCard = createStreamingCard;
