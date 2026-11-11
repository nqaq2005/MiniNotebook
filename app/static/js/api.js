/**
 * api.js - Centralized API calls for backend communication
 */

const Api = {
  async getStats() {
    const res = await fetch('/api/stats');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  },

  async ingestArxiv(query, maxPapers) {
    const res = await fetch('/api/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, max_papers: maxPapers })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `Server trả về mã lỗi HTTP ${res.status}`);
    return data;
  },

  async uploadPdf(formData) {
    const res = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `Server trả về mã lỗi HTTP ${res.status}`);
    return data;
  },

  async deletePaper(paperId) {
    const res = await fetch(`/api/papers/${encodeURIComponent(paperId)}`, {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json().catch(() => ({}));
  },

  async askStream(payload, signal) {
    return await fetch('/api/ask/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal
    });
  }
};

window.Api = Api;
