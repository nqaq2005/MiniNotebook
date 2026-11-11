/**
 * theme.js - Dark/Light theme switching and state persistence
 */

const isDark = () => document.documentElement.getAttribute('data-theme') !== 'light';

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  try { localStorage.setItem('scholar_theme', theme); } catch (e) {}
  const sun = document.getElementById('icon-theme-sun');
  const moon = document.getElementById('icon-theme-moon');
  if (sun) sun.classList.toggle('hidden', theme !== 'dark');
  if (moon) moon.classList.toggle('hidden', theme === 'dark');
  if (typeof styleLangButtons === 'function') styleLangButtons();
  if (typeof styleIngestTabs === 'function') styleIngestTabs(window.currentIngestTab || 'arxiv');
  if (typeof renderSettingsControls === 'function') renderSettingsControls();
}

function toggleTheme() {
  applyTheme(isDark() ? 'light' : 'dark');
}

window.isDark = isDark;
window.applyTheme = applyTheme;
window.toggleTheme = toggleTheme;
