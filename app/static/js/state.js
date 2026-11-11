/**
 * state.js - Centralized application state and localStorage helpers
 */

window.globalState = {
  papers: [],
  lastCitations: []
};

window.showAllLabels = true;
window.currentLanguage = localStorage.getItem('mininotebook_lang') || localStorage.getItem('scholar_lang') || 'vi';

window.currentIngestTab = 'arxiv';
window.activeController = null;
