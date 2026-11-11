// Taigi narration, read-along subtitles and historical pictures for the feature pages.
// A page calls TGNarration({...}) once and then reports its clock to it:
//   name       'dutch' -> window.NARRATION_dutch (narration-dutch.js), audio/dutch/<id>.mp3, PICTURES.dutch
//   cues       [{y, id}] : when each clip starts, in the page's own time unit
//   getT, isPlaying, setPlaying, lang : the page's clock, play state and language ('zh' | 'en' | 'bi')
//   stage, playBtn : the film's .stage element and its play button
// While a clip is speaking the clock keeps moving but waits just before the next cue until the clip ends.
window.TGNarration = function (o) {
  const NARR = window['NARRATION_' + o.name] || {};
  const voice = typeof Audio === 'function' ? new Audio() : null;
  const cues = o.cues.filter(c => NARR[c.id]).sort((a, b) => a.y - b.y || (a.id[0] === 'p' ? -1 : 1));   // phase text before the event at the same moment
  const hasNarr = !!voice && cues.length > 0;
  const cueY = Object.fromEntries(o.cues.map(c => [c.id, c.y]));
  const pics = ((window.PICTURES || {})[o.name] || []).map(p => ({ ...p, t: p.at != null ? cueY[p.at] : p.t })).filter(p => p.t != null).sort((a, b) => a.t - b.t);
  const SILENCE = 'data:audio/wav;base64,UklGRjQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YRAAAAAAAAAAAAAAAAAAAAAAAAAA';
  const SPOKEN = /[㐀-鿿\u{20000}-\u{2fa1f}A-Za-z0-9]/u;
  const UI = {
    on: ['🔊 台語旁白：開', '🔊 Taigi narration: on'], off: ['🔇 台語旁白：關', '🔇 Taigi narration: off'],
    hint: ['按「播放」開始。台語旁白會跟著動畫念，每講完一段，時間才繼續往前走。', 'Press Play to begin. The Taiwanese (Taigi) narration follows the animation, and time moves on when each passage ends.'],
    blocked: ['瀏覽器擋住了聲音，請再按一次「播放」。', 'The browser blocked the sound. Press Play again.'],
    missing: ['找不到旁白音檔（audio 資料夾），動畫照常播放。', 'Narration audio (the audio folder) was not found; the animation plays without it.'],
  };
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const html = ([zh, en]) => { const l = o.lang(); return l === 'en' ? esc(en) : l === 'bi' ? `${esc(zh)}<span class="en" lang="en">${esc(en)}</span>` : esc(zh); };

  if (!document.getElementById('tg-css')) {
    const st = document.createElement('style'); st.id = 'tg-css';
    st.textContent = `
.tg-under { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(0, 1fr); gap: 14px; align-items: stretch; }
.tg-under > .tg-sub[hidden] + .tg-pic, .tg-under > .tg-sub:only-child { grid-column: 1 / -1; }
.tg-under.solo { grid-template-columns: minmax(0, 1fr); }
@media (max-width: 760px) { .tg-under { grid-template-columns: minmax(0, 1fr); } }
.tg-sub { border: 1px solid var(--line); border-left: 3px solid var(--gold, #ecd04f); border-radius: 6px; background: var(--panel); padding: 12px 16px; min-height: 5.2em; display: grid; gap: 4px; align-content: center; min-width: 0; }
.tg-sub[hidden], .tg-pic[hidden], .tg-under[hidden] { display: none; }
.tg-sub p { margin: 0; overflow-wrap: anywhere; }
.tg-sub .s-han { font-family: var(--f-display); font-size: clamp(17px, 2.1vw, 21px); line-height: 1.6; letter-spacing: .03em; color: var(--ink); }
.tg-sub .s-poj { color: var(--muted); font-size: 14px; line-height: 1.55; }
.tg-sub.idle .s-han { font-family: var(--f-body); font-size: 15px; color: var(--muted); letter-spacing: 0; }
.tg-sub.idle .s-han .en { display: block; margin-left: 0; }
.tg-sub.live .s-han span { color: #6f858f; transition: color .12s linear; }
.tg-sub.live .s-han span.done { color: var(--ink); }
.tg-sub.live .s-han span.now { color: var(--gold, #ecd04f); text-shadow: 0 0 14px rgba(236,208,79,.45); }
.tg-sub.live .s-poj span { transition: color .15s linear; }
.tg-sub.live .s-poj span.now { color: var(--ink); }
.tg-pic { margin: 0; border: 1px solid var(--line); border-radius: 6px; background: var(--panel); padding: 10px; display: grid; gap: 8px; align-content: start; min-width: 0; }
.tg-pic .p-img { display: block; height: 210px; background: #061017; border-radius: 4px; overflow: hidden; }
.tg-pic img { width: 100%; height: 100%; object-fit: contain; display: block; }
.tg-pic figcaption { font-size: 13px; line-height: 1.55; color: var(--muted); }
.tg-pic .p-cap { display: block; color: var(--ink); }
.tg-pic .p-cap .en { display: block; margin-left: 0; }
.tg-pic .p-credit { display: block; font-size: 11.5px; margin-top: 4px; overflow-wrap: anywhere; }
.tg-pic .p-credit a { color: var(--muted); }
button.tg-narr[aria-pressed="true"] { border-color: var(--gold, #ecd04f); color: var(--gold, #ecd04f); }
button.tg-narr[hidden] { display: none; }`;
    document.head.appendChild(st);
  }
  const mk = (tag, cls, attrs) => { const e = document.createElement(tag); if (cls) e.className = cls; for (const k in (attrs || {})) e.setAttribute(k, attrs[k]); return e; };
  const under = mk('div', 'tg-under'), box = mk('div', 'tg-sub idle', { 'aria-live': 'off' });
  const han = mk('p', 's-han', { lang: 'nan-Hant' }), poj = mk('p', 's-poj', { lang: 'nan-Latn' });
  box.append(han, poj); under.appendChild(box);
  const fig = mk('figure', 'tg-pic'), pa = mk('a', 'p-img', { target: '_blank', rel: 'noopener' }), img = mk('img', '', { alt: '' });
  const fc = mk('figcaption'), cap = mk('span', 'p-cap'), cred = mk('span', 'p-credit');
  pa.appendChild(img); fc.append(cap, cred); fig.append(pa, fc); fig.hidden = true; under.appendChild(fig);
  o.stage.insertAdjacentElement('afterend', under);
  const btn = mk('button', 'tg-narr', { type: 'button' });
  o.playBtn.insertAdjacentElement('afterend', btn);

  let narrOn = hasNarr, unlocked = false, idx = 0, speaking = null, shown = null, gapUntil = 0, key = 'hint', hl = null, picShown;
  try { if (localStorage.getItem('tw400-narr') === 'off') narrOn = false; } catch (e) {}

  function showSub() {
    box.hidden = !hasNarr || !narrOn;
    box.classList.toggle('idle', !shown);
    const n = shown && NARR[shown.id];
    box.classList.toggle('live', !!n);
    hl = null; han.textContent = ''; poj.textContent = '';
    if (!n) { han.innerHTML = html(UI[key]); layoutUnder(); return; }
    const chars = [], segs = [];
    n.segs.forEach(([h, p, pj, a, b], si) => {
      const mine = [];
      for (const ch of Array.from(h + p)) {
        const sp = document.createElement('span'); sp.textContent = ch; han.appendChild(sp);
        const c = { el: sp, si, t: 0, state: '' }; chars.push(c);
        if (SPOKEN.test(ch)) mine.push(c); else c.follow = true;       // punctuation lights up with the character before it
      }
      mine.forEach((c, i) => { c.t = a + (b - a) * i / mine.length; });   // inside a clause the characters share the time evenly
      const ps = document.createElement('span'); ps.textContent = pj + (/[。！？]/.test(p) ? '. ' : p ? ', ' : ' '); poj.appendChild(ps);
      segs.push({ el: ps, on: false });
    });
    let t = 0; for (const c of chars) { if (c.follow) c.t = t; else t = c.t; }
    hl = { chars, segs }; readAlong(); layoutUnder();
  }
  function readAlong() {
    if (!hl) return;
    const t = speaking ? voice.currentTime : Infinity;   // after the clip ends everything stays lit
    let cur = -1; for (let i = 0; i < hl.chars.length; i++) { if (hl.chars[i].t <= t) cur = i; else break; }
    while (cur > 0 && hl.chars[cur].follow) cur--;
    const curSeg = cur >= 0 && speaking ? hl.chars[cur].si : -1;
    hl.chars.forEach((c, i) => {
      const st = !speaking || i < cur ? 'done' : i === cur ? 'now' : c.follow && c.t <= t ? 'done' : '';
      if (st !== c.state) { c.state = st; c.el.className = st; }
    });
    hl.segs.forEach((g, i) => { const on = i === curSeg; if (on !== g.on) { g.on = on; g.el.className = on ? 'now' : ''; } });
  }
  function showPic(force) {
    const t = o.getT(); let p = null; for (const x of pics) { if (x.t <= t + 1e-9) p = x; else break; }
    if (p === picShown && !force) return;
    picShown = p; fig.hidden = !p; layoutUnder(); if (!p) return;
    img.src = 'images/' + p.key + '.jpg'; img.alt = o.lang() === 'en' ? p.en : p.zh; pa.href = p.url;
    cap.innerHTML = html([p.zh, p.en]);
    cred.textContent = (/unknown/i.test(p.artist) || !p.artist ? '' : p.artist + ' · ') + p.license + ' · ';
    const l = mk('a', '', { href: p.url, target: '_blank', rel: 'noopener' }); l.textContent = 'Wikimedia Commons'; cred.appendChild(l);
    const n = pics[pics.indexOf(p) + 1]; if (n && typeof Image === 'function') new Image().src = 'images/' + n.key + '.jpg';   // have the next one ready
  }
  function layoutUnder() { under.hidden = box.hidden && fig.hidden; under.classList.toggle('solo', box.hidden || fig.hidden); }
  function resetCues() { const t = o.getT(); idx = cues.findIndex(c => c.y >= t - 0.02); if (idx < 0) idx = cues.length; }
  function stopVoice() { if (!voice) return; voice.pause(); speaking = shown = null; gapUntil = 0; showSub(); }
  function failed(name) {
    const cue = speaking; speaking = shown = null;
    key = name === 'NotAllowedError' ? 'blocked' : 'missing'; showSub();
    if (name === 'NotAllowedError') { unlocked = false; idx = Math.max(0, cues.indexOf(cue)); o.setPlaying(false); }
  }
  function speak(cue) {
    speaking = shown = cue; key = 'hint'; showSub();
    voice.src = 'audio/' + o.name + '/' + cue.id + '.mp3';
    const p = voice.play();
    if (p) p.catch(err => { if (speaking === cue && err.name !== 'AbortError') failed(err.name); });
  }
  function applyBtn() {
    btn.hidden = !hasNarr; btn.setAttribute('aria-pressed', narrOn);
    btn.innerHTML = html(UI[narrOn ? 'on' : 'off']);
  }
  if (voice) {
    voice.preload = 'auto';
    voice.addEventListener('ended', () => { if (speaking) { speaking = null; gapUntil = performance.now() + 450; } });
    voice.addEventListener('error', () => { if (speaking) failed('missing'); });
  }
  const api = {
    on: () => narrOn,
    busy: () => narrOn && !!speaking,
    unlock() {   // phones only let a page start sound from inside a tap
      if (!hasNarr || !narrOn || unlocked || speaking) return;
      unlocked = true; voice.src = SILENCE; const p = voice.play(); if (p) p.catch(() => {});
    },
    sync() {     // follow the page's play / pause
      if (!voice || !speaking) return;
      if (o.isPlaying() && narrOn) { if (voice.paused) { const p = voice.play(); if (p) p.catch(() => {}); } }
      else voice.pause();
    },
    seek() { stopVoice(); resetCues(); showPic(); },
    // how far the clock may move this frame; starts the next clip when its moment is reached
    step(step, now) {
      if (!narrOn) return step;
      const next = cues[idx], t = o.getT();
      if (!next || t + step < next.y) return step;
      if (speaking || now < gapUntil) return Math.max(0, next.y - 0.0005 - t);
      idx++; speak(next);
      return next.y - t;
    },
    tick() { readAlong(); showPic(); },
    lang() { applyBtn(); showSub(); showPic(true); },
  };
  btn.addEventListener('click', () => {
    narrOn = hasNarr && !narrOn; try { localStorage.setItem('tw400-narr', narrOn ? 'on' : 'off'); } catch (e) {}
    stopVoice(); resetCues(); applyBtn(); if (narrOn && o.isPlaying()) api.unlock();
  });
  applyBtn(); showSub(); resetCues();
  return api;
};
