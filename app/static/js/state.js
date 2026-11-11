/**
 * state.js - Centralized application state and localStorage helpers
 */

window.globalState = {
  papers: [],
  lastCitations: []
};

window.showAllLabels = true;
window.currentLanguage = localStorage.getItem('scholar_lang') || 'vi';

try {
  window.notes = JSON.parse(localStorage.getItem('scholar_notes') || '[]');
} catch (e) {
  window.notes = [];
}

window.currentIngestTab = 'arxiv';
window.activeController = null;
