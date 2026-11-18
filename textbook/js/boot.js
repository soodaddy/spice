'use strict';
/* boot.js - build each widget lazily, shortly before it scrolls into view (keeps the first paint fast). */
(function () {
  const mount = (el) => {
    if (el.dataset.mounted) return; el.dataset.mounted = '1';
    const key = el.id.replace(/^ia-/, '');
    try { el.innerHTML = ''; window.IA.W[key](el); }
    catch (e) { el.textContent = '시각화를 불러오지 못했습니다: ' + e.message; console.error(e); }
  };
  const targets = [...document.querySelectorAll('.ia[id^="ia-"]')];
  if (!('IntersectionObserver' in window)) { targets.forEach(mount); return; }
  const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { mount(e.target); io.unobserve(e.target); } }), { rootMargin: '700px' });
  targets.forEach((t) => io.observe(t));
  window.__iaMountAll = () => targets.forEach(mount);   // used by the tests
})();
