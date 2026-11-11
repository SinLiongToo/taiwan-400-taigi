// Smoke test: run a page's inline scripts against a stub DOM at a given width,
// render many animation frames, and report any runtime error.
// Usage: node tools/smoke.js <page.html> [width]
const fs = require('fs');
const [,, file, widthArg] = process.argv;
const width = +widthArg || 1300;
const html = fs.readFileSync(file, 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
// the shared narration module is loaded from a file; run it too so its page hooks are exercised
if (/<script src="tg\.js">/.test(html)) scripts.unshift(fs.readFileSync(require('path').join(require('path').dirname(file), 'tg.js'), 'utf8'));

const ctx2d = new Proxy({}, {
  get(t, k) {
    if (k in t) return t[k];
    if (k === 'measureText') return s => ({ width: String(s).length * 9 });
    if (k === 'createRadialGradient' || k === 'createLinearGradient') return () => ({ addColorStop() {} });
    return typeof k === 'string' && /^[a-z]/.test(k) ? () => {} : undefined;
  },
  set(t, k, v) { t[k] = v; return true; },
});
const els = {};
function el(id) {
  if (!els[id]) els[id] = {
    id, dataset: {}, style: {}, value: '0', textContent: '', innerHTML: '', hidden: false, clientWidth: width,
    parentElement: { clientWidth: width }, classList: { toggle() {}, add() {}, remove() {} },
    getContext: () => ctx2d, setAttribute() {}, addEventListener() {}, appendChild() {}, append() {}, insertAdjacentElement() {},
    scrollIntoView() {}, matches: () => false, querySelector: () => el('q'),
  };
  return els[id];
}
const dataKs = [...html.matchAll(/data-k="(\w+)"/g)].map(m => m[1]);
global.window = global;
global.document = {
  getElementById: el, documentElement: el('html'), head: el('head'), title: '',
  querySelector: () => el('q'),
  querySelectorAll: sel => sel === '[data-k]' ? dataKs.map(k => Object.assign(el('k_' + k), { dataset: { k } })) : [],
  createElement: () => el('new' + Math.random()), addEventListener() {},
};
global.location = { hash: '' };
global.localStorage = { getItem: () => null, setItem() {} };
global.matchMedia = () => ({ matches: false });
global.devicePixelRatio = 1;
global.Image = function () { this.complete = true; this.naturalWidth = 160; };
global.ResizeObserver = class { observe() {} };
global.IntersectionObserver = class { constructor(cb) { this.cb = cb; } observe(t) { this.cb([{ isIntersecting: true, target: t }]); } };
const frames = [];
global.requestAnimationFrame = f => frames.push(f);
global.MediaRecorder = undefined;
try {
  for (const s of scripts) eval(s);
  let now = 0;
  for (let i = 0; i < 4000 && frames.length; i++) { const f = frames.shift(); now += 100; f(now); }
  console.log(`${file} @${width}px: ran ${now / 100} frames OK`);
} catch (e) {
  console.log(`${file} @${width}px: ERROR`, e && e.stack ? e.stack.split('\n').slice(0, 4).join('\n') : e);
  process.exit(1);
}
