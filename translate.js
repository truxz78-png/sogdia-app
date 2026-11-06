/* Sogdia automatic translation for the info pages (Privacy Policy, Terms of Service).
 * Same method as the home page: no Google widget, no banner.
 * - Detects the phone/browser language and translates the visible text.
 * - Never translates elements marked translate="no" or class "notranslate",
 *   brand names, e-mail addresses or web addresses.
 * - Saves translations on the device so each text is requested only once.
 * - If anything fails, the page simply stays in English (the official version).
 */
(function () {
  'use strict';
  var lang = String(navigator.language || navigator.userLanguage || 'en').split('-')[0].toLowerCase();
  if (!lang || lang === 'en') return;

  var KEEP = {};
  ['sogdia', 'driftforgedev', 'github', 'github pages', 'google', 'admitad',
   'involve asia', 'inrdeals'].forEach(function (b) { KEEP[b] = true; });
  var SKIP = /^(script|style|noscript|code|pre|textarea)$/i;
  var NOT_TEXT = /^[\d\s.,·©%+\-–—…:;()\/]+$|@|^https?:|\.(com|html)$/i;
  var KEY = 'tr_page_' + lang;
  var cache = {};
  try { cache = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (e) { cache = {}; }

  function skipped(node) {
    for (var el = node.parentElement; el; el = el.parentElement) {
      if (SKIP.test(el.tagName)) return true;
      if (el.getAttribute('translate') === 'no') return true;
      if (el.classList && el.classList.contains('notranslate')) return true;
    }
    return false;
  }

  function tr(text) {
    if (cache[text]) return Promise.resolve(cache[text]);
    var url = 'https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=' +
      encodeURIComponent(lang) + '&dt=t&q=' + encodeURIComponent(text);
    return fetch(url).then(function (r) { return r.json(); }).then(function (j) {
      var out = j[0].map(function (x) { return x[0]; }).join('');
      if (/^[A-Z]/.test(text) && out) out = out.charAt(0).toUpperCase() + out.slice(1);
      if (out) cache[text] = out;
      return out || text;
    });
  }

  function run() {
    var nodes = [];
    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
    while (walker.nextNode()) {
      var n = walker.currentNode, t = n.nodeValue.trim();
      if (!t || t.length < 2 || NOT_TEXT.test(t) || KEEP[t.toLowerCase()] || skipped(n)) continue;
      nodes.push(n);
    }
    var i = 0;
    function worker() {
      if (i >= nodes.length) return Promise.resolve();
      var n = nodes[i++], orig = n.nodeValue, t = orig.trim();
      return tr(t).then(function (out) { n.nodeValue = orig.replace(t, out); }, function () {})
        .then(worker);
    }
    var jobs = [];
    for (var k = 0; k < 6; k++) jobs.push(worker());
    jobs.push(tr(document.title.replace(/^Sogdia – /, '')).then(function (out) {
      document.title = 'Sogdia – ' + out;
    }, function () {}));
    Promise.all(jobs).then(function () {
      document.documentElement.lang = lang;
      try { localStorage.setItem(KEY, JSON.stringify(cache)); } catch (e) {}
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run);
  else run();
})();
