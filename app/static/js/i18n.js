/**
 * i18n.js - Multi-language translation engine and dictionaries
 */

const UI_TRANSLATIONS = {
  'Đang kiểm tra...': 'Checking...',
  'Cài đặt': 'Settings',
  'Truy xuất, mô hình ngôn ngữ và giao diện.': 'Retrieval, language models, and appearance.',
  'Nguồn': 'Sources',
  'Thêm nguồn': 'Add source',
  'Lọc nguồn...': 'Filter sources...',
  'chunks': 'chunks',
  'nodes': 'nodes',
  'links': 'links',
  'Trò chuyện': 'Chat',
  'Ghi chú Markdown': 'Markdown notes',
  'Sổ tay nghiên cứu': 'Research notebook',
  '0 nguồn': '0 sources',
  'Đặt câu hỏi, so sánh và tổng hợp các bài báo trong thư viện. Mỗi câu trả lời đều có trích dẫn đến đúng mục và trang của nguồn.': 'Ask questions, compare, and synthesize papers in your library. Every answer includes citations to the relevant source section and page.',
  'Bắt đầu nhập...': 'Start typing...',
  'MiniNotebook có thể mắc lỗi. Hãy đối chiếu với nguồn trích dẫn.': 'MiniNotebook can make mistakes. Please verify answers against the cited sources.',
  'Chi tiết': 'Details',
  'Đã lưu': 'Saved',
  'Đang lưu...': 'Saving...',
  '0 từ': '0 words',
  '0 ký tự': '0 characters',
  '1 dòng': '1 line',
  'Đã chép Markdown': 'Markdown copied',
  'Nội dung xem trước sẽ hiển thị ở đây...': 'Your preview will appear here...',
  'Nạp bài báo vào sổ tay để hỏi đáp và trích dẫn.': 'Add papers to your notebook for Q&A and citations.',
  'Tìm trên ArXiv': 'Search ArXiv',
  'Tải PDF lên': 'Upload PDF',
  'Chủ đề gợi ý': 'Suggested topics',
  'Từ khóa hoặc ArXiv ID': 'Keyword or ArXiv ID',
  'Số bài báo cần tải': 'Number of papers to fetch',
  'Tối đa 8 bài mỗi lần': 'Up to 8 papers per request',
  'Tải & lập chỉ mục': 'Fetch & index',
  'Kéo thả file PDF vào đây': 'Drag and drop a PDF here',
  'hoặc': 'or',
  'chọn từ máy tính': 'browse files',
  'Tiêu đề tùy chỉnh': 'Custom title',
  '(không bắt buộc)': '(optional)',
  'Phân tích bằng RapidOCR & lập chỉ mục': 'Process with RapidOCR & index',
  'Truy xuất': 'Retrieval',
  'Khuyên dùng': 'Recommended',
  'Chỉ vector ngữ nghĩa (BGE-Small ONNX)': 'Semantic vectors only (BGE-Small ONNX)',
  'Chỉ từ khóa (BM25Okapi)': 'Keyword search only (BM25Okapi)',
  'Mô hình ngôn ngữ': 'Language model',
  'Nhà cung cấp': 'Provider',
  'Tên model': 'Model name',
  '(chỉ khi chọn Custom)': '(only for Custom)',
  '(ghi đè khóa trong .env)': '(overrides the key in .env)',
  'Suy luận': 'Reasoning',
  'Tắt': 'Off',
  'Thấp': 'Low',
  'Vừa': 'Medium',
  'Cao': 'High',
  'Giao diện': 'Appearance',
  'Chủ đề màu': 'Color theme',
  'Sáng': 'Light',
  'Tối': 'Dark',
  'Cài đặt áp dụng cho các câu hỏi tiếp theo.': 'Settings apply to subsequent questions.',
  'Xong': 'Done',
  'Thu gọn': 'Collapse',
  'Mở thanh nguồn': 'Open sources panel',
  'Xóa cuộc trò chuyện': 'Clear conversation',
  'Ẩn/hiện Soạn thảo Markdown': 'Toggle Markdown editor',
  'Chuyển Dark / Light': 'Toggle dark / light mode',
  'Vị trí hiển thị ghi chú': 'Note display mode',
  'Chia đôi với khung chat': 'Split with chat',
  'Phủ toàn bộ khung chat': 'Cover the chat area',
  'Chế độ soạn thảo': 'Editor mode',
  'Chỉ soạn thảo': 'Editor only',
  'Chia đôi màn hình': 'Split view',
  'Xem trước tài liệu': 'Preview document',
  'Sao chép toàn bộ Markdown': 'Copy all Markdown',
  'Tải về file .md': 'Download .md file',
  'Đóng ghi chú': 'Close notes',
  'Đóng (Esc)': 'Close (Esc)',
  'Giảm': 'Decrease',
  'Tăng': 'Increase',
  'Bấm để đổi tên tài liệu': 'Click to rename document',
  'Ngôn ngữ trả lời': 'Response language',
  'Hiện/ẩn khóa': 'Show/hide key',
  'Xóa nguồn': 'Remove source',
  'Chèn vào Markdown': 'Insert into Markdown',
  'Sao chép': 'Copy',
  'Tự nhận diện từ PDF nếu để trống': 'Auto-detect from PDF if left blank',
  'Để trống để dùng khóa trong .env': 'Leave blank to use the key in .env',
  "# Bắt đầu ghi chú tại đây...\n\nBạn có thể tự do gõ Markdown hoặc bấm 'Chèn vào Markdown' từ bất kỳ câu trả lời nào của AI bên cạnh.": "# Start writing your note here...\n\nYou can write Markdown freely or click 'Insert into Markdown' from any AI answer beside it.",
  'VD: GraphRAG, 3D Gaussian Splatting, 2305.14314': 'e.g. GraphRAG, 3D Gaussian Splatting, 2305.14314',
  'VD: http://localhost:11434/v1': 'e.g. http://localhost:11434/v1',
  'Không có nguồn nào khớp bộ lọc.': 'No sources match your filter.',
  'Các nguồn đã lưu sẽ hiển thị ở đây.<br>Thêm bài báo để bắt đầu.': 'Saved sources will appear here.<br>Add papers to get started.',
  '+ Thêm nguồn đầu tiên': '+ Add first source',
  'Hướng dẫn nguồn': 'Source guide',
  'Tóm tắt': 'Abstract',
  'Cấu trúc tài liệu': 'Document structure',
  'Xuất bản:': 'Published:',
  'Trích dẫn:': 'Citations:',
  'Chunks:': 'Chunks:',
  'Không rõ tác giả': 'Unknown author',
  'Chào mừng bạn đến với khu vực': 'Welcome to the',
  'Đang tải & phân tích PDF...': 'Loading & analyzing PDF...',
  'Đang phân tích PDF...': 'Analyzing PDF...',
  'Đang chạy layout parser & RapidOCR...': 'Running layout parser & RapidOCR...',
  'Không thể kết nối đến server. Vui lòng kiểm tra terminal chạy server!': 'Cannot connect to the server. Please check the server terminal!',
  'Dừng': 'Stop',
  'Gửi': 'Send',
  'Đang tìm trong nguồn…': 'Searching sources…',
  'Đang tìm trong nguồn...': 'Searching sources...',
  'Đang tìm trong nguồn (Hybrid + Cross-Encoder)…': 'Searching sources (Hybrid + Cross-Encoder)…',
  'Đang suy luận…': 'Reasoning…',
  'Đang suy luận...': 'Reasoning...',
  'Quá trình suy luận': 'Reasoning process',
  'Đang tạo câu trả lời…': 'Generating answer…',
  'Đang chờ token đầu tiên…': 'Waiting for the first token…',
  '✓ Đã chèn': '✓ Inserted',
  '✓ Đã chép': '✓ Copied',
  '✓ Trích dẫn đã xác minh': '✓ Verified citation',
  'Trích dẫn đã xác minh': 'Verified citation',
  'Đoạn trích nguồn': 'Source excerpt',
  'Lỗi': 'Error',
  'Đã dừng': 'Stopped',
  'đã dừng sau': 'stopped after',
  'Chưa có câu trả lời.': 'No answer yet.',
  'Mô hình đang suy luận — câu trả lời sẽ hiện ở đây…': 'The model is reasoning — the answer will appear here…',
  'Bạn có chắc muốn xóa toàn bộ nội dung trong bản ghi chú này?': 'Are you sure you want to clear all content in this note?',
  'Chọn ngôn ngữ giao diện': 'Choose interface language',
  'Google Gemini': 'Google Gemini',
  'OpenAI': 'OpenAI',
  'DeepSeek': 'DeepSeek',
  'Groq': 'Groq',
  'OpenRouter': 'OpenRouter',
  'Ollama / vLLM': 'Ollama / vLLM',
  'Custom endpoint': 'Custom endpoint'
};

const UI_ATTRIBUTE_TRANSLATIONS = {
  'Bắt đầu nhập...': 'Start typing...',
  'Lọc nguồn...': 'Filter sources...',
  'Tự nhận diện từ PDF nếu để trống': 'Auto-detect from PDF if left blank',
  'Để trống để dùng khóa trong .env': 'Leave blank to use the key in .env',
  'VD: http://localhost:11434/v1': 'e.g. http://localhost:11434/v1',
  'Chuyển Dark / Light': 'Toggle dark / light mode',
  'Thu gọn': 'Collapse',
  'Mở thanh nguồn': 'Open sources panel',
  'Xóa cuộc trò chuyện': 'Clear conversation',
  'Ẩn/hiện Soạn thảo Markdown': 'Toggle Markdown editor',
  'Ngôn ngữ trả lời': 'Response language',
  'Vị trí hiển thị ghi chú': 'Note display mode',
  'Chia đôi với khung chat': 'Split with chat',
  'Phủ toàn bộ khung chat': 'Cover the chat area',
  'Chế độ soạn thảo': 'Editor mode',
  'Chỉ soạn thảo': 'Editor only',
  'Chia đôi màn hình': 'Split view',
  'Xem trước tài liệu': 'Preview document',
  'Sao chép toàn bộ Markdown': 'Copy all Markdown',
  'Tải về file .md': 'Download .md file',
  'Đóng ghi chú': 'Close notes',
  'Đóng (Esc)': 'Close (Esc)',
  'Giảm': 'Decrease',
  'Tăng': 'Increase',
  'Bấm để đổi tên tài liệu': 'Click to rename document',
  'Hiện/ẩn khóa': 'Show/hide key',
  'Xóa nguồn': 'Remove source',
  'Dừng': 'Stop',
  'Gửi': 'Send',
  'Sao chép': 'Copy',
  'Chèn vào Markdown': 'Insert into Markdown'
};

const UI_ENGLISH_TO_VI = Object.fromEntries(Object.entries(UI_TRANSLATIONS).map(([vi, en]) => [en, vi]));
const UI_ATTRIBUTES_EN_TO_VI = Object.fromEntries(Object.entries(UI_ATTRIBUTE_TRANSLATIONS).map(([vi, en]) => [en, vi]));
const uiOriginalTextNodes = new WeakMap();
const uiOriginalAttributes = new WeakMap();

function t(key) {
  if (!key) return '';
  const lang = window.currentLanguage || 'vi';
  if (lang === 'en') {
    return UI_TRANSLATIONS[key] || key;
  }
  return UI_ENGLISH_TO_VI[key] || key;
}

function translateTextNode(node) {
  if (!node || !node.nodeValue || !node.nodeValue.trim()) return;
  const parent = node.parentElement;
  if (!parent || parent.closest('script,style,textarea,input,code,pre,[contenteditable="true"],#md-editor,#md-preview,[data-role="answer"],[data-role="thinking"],.user-bubble')) return;
  let state = uiOriginalTextNodes.get(node);
  if (!state || node.nodeValue !== state.lastApplied) {
    state = { original: node.nodeValue, lastApplied: node.nodeValue };
    uiOriginalTextNodes.set(node, state);
  }
  const original = state.original;
  const key = original.trim();
  const lang = window.currentLanguage || 'vi';
  const translated = lang === 'en' ? (UI_TRANSLATIONS[key] || key) : (UI_ENGLISH_TO_VI[key] || key);
  const nextValue = original.replace(key, translated);
  if (node.nodeValue !== nextValue) node.nodeValue = nextValue;
  state.lastApplied = nextValue;
}

function translateElementAttributes(root) {
  if (!root || root.nodeType !== 1) return;
  const attrs = ['title', 'placeholder', 'aria-label', 'data-tooltip'];
  const elements = [root, ...root.querySelectorAll('*')];
  const lang = window.currentLanguage || 'vi';
  for (const el of elements) {
    for (const attr of attrs) {
      const value = el.getAttribute && el.getAttribute(attr);
      if (!value) continue;
      let attrState = uiOriginalAttributes.get(el);
      if (!attrState) { attrState = {}; uiOriginalAttributes.set(el, attrState); }
      if (!attrState[attr] || value !== attrState[attr].lastApplied) attrState[attr] = { original: value, lastApplied: value };
      const original = attrState[attr].original;
      const translated = lang === 'en'
        ? (UI_ATTRIBUTE_TRANSLATIONS[original] || UI_TRANSLATIONS[original] || original)
        : (UI_ATTRIBUTES_EN_TO_VI[original] || UI_ENGLISH_TO_VI[original] || original);
      if (value !== translated) el.setAttribute(attr, translated);
      attrState[attr].lastApplied = translated;
    }
  }
}

function translateInterface() {
  const lang = window.currentLanguage || 'vi';
  const isEnglish = lang === 'en';
  document.documentElement.lang = lang;
  document.title = 'MiniNotebook';

  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) translateTextNode(node);
  translateElementAttributes(document.body);

  const input = document.getElementById('question-input');
  if (input) input.placeholder = isEnglish ? 'Start typing...' : 'Bắt đầu nhập...';
  const langGroup = document.querySelector('[aria-label="Choose interface language"], [aria-label="Chọn ngôn ngữ giao diện"]');
  if (langGroup) langGroup.setAttribute('aria-label', isEnglish ? 'Choose interface language' : 'Chọn ngôn ngữ giao diện');

  // Update existing dynamic chat action buttons & badges
  document.querySelectorAll('#qa-results [data-act="save"]').forEach(btn => {
    btn.innerHTML = `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg> ${t('Chèn vào Markdown')}`;
  });
  document.querySelectorAll('#qa-results [data-act="copy"]').forEach(btn => {
    btn.textContent = t('Sao chép');
  });
  document.querySelectorAll('#qa-results [data-role="badge"]').forEach(badge => {
    const text = badge.textContent.trim();
    if (text === '✓ Trích dẫn đã xác minh' || text === '✓ Verified citation') {
      badge.textContent = t('✓ Trích dẫn đã xác minh');
    } else if (text === 'Đoạn trích nguồn' || text === 'Source excerpt') {
      badge.textContent = t('Đoạn trích nguồn');
    } else if (text === 'Đang tìm trong nguồn…' || text === 'Searching sources…') {
      badge.textContent = t('Đang tìm trong nguồn…');
    } else if (text === 'Đang tạo câu trả lời…' || text === 'Generating answer…') {
      badge.textContent = t('Đang tạo câu trả lời…');
    } else if (text === 'Đang chờ token đầu tiên…' || text === 'Waiting for the first token…') {
      badge.textContent = t('Đang chờ token đầu tiên…');
    } else if (text === 'Đã dừng' || text === 'Stopped') {
      badge.textContent = t('Đã dừng');
    } else if (text === 'Lỗi' || text === 'Error') {
      badge.textContent = t('Lỗi');
    }
  });

  document.querySelectorAll('#qa-results [data-role="sources-label"]').forEach(el => {
    const match = el.textContent.match(/\d+/);
    if (match) {
      const count = parseInt(match[0], 10);
      el.textContent = isEnglish
        ? `View ${count} source ${count === 1 ? 'excerpt' : 'excerpts'}`
        : `Xem ${count} đoạn trích nguồn`;
    }
  });

  // Re-render sources list if function exists
  if (typeof renderSourcesList === 'function') {
    renderSourcesList();
  }
}

function styleLangButtons() {
  const lang = window.currentLanguage || 'vi';
  const on = 'px-2.5 py-1 rounded-full font-semibold transition-colors';
  const off = 'px-2.5 py-1 rounded-full t-muted transition-colors';
  const viBtn = document.getElementById('lang-btn-vi');
  const enBtn = document.getElementById('lang-btn-en');
  if (!viBtn || !enBtn) return;
  [[viBtn, 'vi'], [enBtn, 'en']].forEach(([button, l]) => {
    button.className = lang === l ? on : off;
    button.style.background = lang === l ? 'var(--accent)' : 'transparent';
    button.style.color = lang === l ? 'var(--on-accent)' : '';
    button.setAttribute('aria-pressed', lang === l ? 'true' : 'false');
  });
}

function setLanguage(lang) {
  window.currentLanguage = (lang === 'en' ? 'en' : 'vi');
  try { localStorage.setItem('scholar_lang', window.currentLanguage); } catch (e) {}
  const cfg = document.getElementById('cfg-language');
  if (cfg) cfg.value = window.currentLanguage;
  styleLangButtons();
  translateInterface();
  if (typeof renderSettingsControls === 'function') renderSettingsControls();
}

function initI18nObserver() {
  const observer = new MutationObserver(mutations => {
    if (window.currentLanguage !== 'en') return;
    for (const mutation of mutations) {
      if (mutation.type === 'characterData') translateTextNode(mutation.target);
      for (const added of mutation.addedNodes || []) {
        if (added.nodeType === 3) translateTextNode(added);
        else if (added.nodeType === 1) {
          const walker = document.createTreeWalker(added, NodeFilter.SHOW_TEXT);
          let textNode;
          while ((textNode = walker.nextNode())) translateTextNode(textNode);
          translateElementAttributes(added);
        }
      }
    }
  });
  observer.observe(document.body, { subtree: true, childList: true, characterData: true });
}

window.t = t;
window.setLanguage = setLanguage;
window.translateInterface = translateInterface;
window.styleLangButtons = styleLangButtons;
window.initI18nObserver = initI18nObserver;
