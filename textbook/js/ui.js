'use strict';
/* ui.js - colour map, sliders, a tiny canvas plotting class and the widget scaffold. No external libraries. */
(function (G) {
  const MS = G.MS;

  // ---- element helper
  function h(tag, attrs, ...kids) {
    const e = document.createElement(tag);
    for (const k in attrs || {}) {
      if (k === 'class') e.className = attrs[k];
      else if (k === 'html') e.innerHTML = attrs[k];
      else if (k.startsWith('on')) e.addEventListener(k.slice(2), attrs[k]);
      else e.setAttribute(k, attrs[k]);
    }
    for (const c of kids.flat()) if (c != null) e.append(c.nodeType ? c : document.createTextNode(c));
    return e;
  }

  // ---- diverging colour map (RdYlBu reversed): low voltage = blue, high voltage = red
  const STOPS = ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8', '#ffffbf', '#fee090', '#fdae61', '#f46d43', '#d73027', '#a50026']
    .map((s) => [1, 3, 5].map((i) => parseInt(s.slice(i, i + 2), 16)));
  function cmapRGB(t) {
    t = Math.min(1, Math.max(0, isFinite(t) ? t : 0));
    const x = t * (STOPS.length - 1), i = Math.min(STOPS.length - 2, Math.floor(x)), f = x - i;
    return STOPS[i].map((a, k) => a + (STOPS[i + 1][k] - a) * f);
  }
  const cmap = (t) => { const c = cmapRGB(t); return `rgb(${c[0] | 0},${c[1] | 0},${c[2] | 0})`; };
  const shadeRGB = (c, f, a) => `rgba(${Math.min(255, c[0] * f) | 0},${Math.min(255, c[1] * f) | 0},${Math.min(255, c[2] * f) | 0},${a === undefined ? 1 : a})`;

  /** colour-bar canvas element with end labels */
  function colorbar(vmin, vmax, unit) {
    const cv = h('canvas', { class: 'ia-cbar', width: 240, height: 14 }), ctx = cv.getContext('2d');
    for (let x = 0; x < 240; x++) { ctx.fillStyle = cmap(x / 239); ctx.fillRect(x, 0, 1, 14); }
    const wrap = h('div', { class: 'ia-cbar-wrap' }, h('span', {}, `${vmin.toFixed(1)} ${unit || 'V'}`), cv, h('span', {}, `${vmax.toFixed(1)} ${unit || 'V'}`));
    wrap.update = (a, b) => { wrap.children[0].textContent = `${a.toFixed(2)} ${unit || 'V'}`; wrap.children[2].textContent = `${b.toFixed(2)} ${unit || 'V'}`; };
    return wrap;
  }

  // ---- controls
  /** opts: {id,label,min,max,step,value,unit,log,fmt,onInput}. value of a log slider is exp-interpolated. */
  function slider(o) {
    const log = !!o.log, N = 1000;
    const toPos = (v) => (log ? (Math.log(v) - Math.log(o.min)) / (Math.log(o.max) - Math.log(o.min)) * N : v);
    const fromPos = (p) => (log ? Math.exp(Math.log(o.min) + (p / N) * (Math.log(o.max) - Math.log(o.min))) : +p);
    const quant = (v) => (log ? v : Math.round(v / o.step) * o.step);
    const input = h('input', { type: 'range', min: log ? 0 : o.min, max: log ? N : o.max, step: log ? 1 : o.step });
    input.value = toPos(o.value);
    const out = h('output', {});
    const fmt = o.fmt || ((v) => MS.si(v, o.unit || '', 3));
    const wrap = h('label', { class: 'ia-ctl' }, h('span', { class: 'ia-lab', html: o.label }), out, input);
    let cur = o.value;   // the exact value; a log slider's position only has 1000 steps, so the default must not be re-derived from it
    const api = { el: wrap, id: o.id, get: () => cur, set(v) { cur = v; input.value = toPos(v); show(); }, input, setRange(min, max) { o.min = min; o.max = max; if (!log) { input.min = min; input.max = max; } show(); } };
    const show = () => { out.textContent = fmt(api.get()); };
    input.addEventListener('input', () => { cur = quant(fromPos(input.value)); show(); if (o.onInput) o.onInput(cur); });
    show();
    return api;
  }
  function select(o) { // {label, options:[[value,text]], value, onInput}
    const sel = h('select', {}, o.options.map(([v, t]) => h('option', { value: v }, t)));
    sel.value = o.value;
    sel.addEventListener('input', () => o.onInput && o.onInput(sel.value));
    return { el: h('label', { class: 'ia-ctl' }, h('span', { class: 'ia-lab', html: o.label }), sel), get: () => sel.value, set(v) { sel.value = v; } };
  }
  function button(text, onClick, cls) { return h('button', { type: 'button', class: 'ia-btn ' + (cls || ''), onclick: onClick }, text); }
  function checkbox(o) {
    const c = h('input', { type: 'checkbox' }); c.checked = !!o.value;
    c.addEventListener('input', () => o.onInput && o.onInput(c.checked));
    return { el: h('label', { class: 'ia-chk' }, c, h('span', { html: o.label })), get: () => c.checked, set(v) { c.checked = v; } };
  }

  // ---- plotting
  const NICE = [1, 2, 2.5, 5, 10];
  function niceTicks(lo, hi, n) {
    const span = hi - lo, raw = span / n, mag = Math.pow(10, Math.floor(Math.log10(raw)));
    let step = mag; for (const f of NICE) { if (raw <= f * mag) { step = f * mag; break; } }
    const out = []; for (let v = Math.ceil(lo / step - 1e-9) * step; v <= hi + 1e-9 * span; v += step) out.push(+v.toPrecision(12));
    return out;
  }
  const fmtTick = (v) => { const a = Math.abs(v); if (a === 0) return '0'; if (a >= 1e4 || a < 1e-3) return v.toExponential(0).replace('e+', 'e'); return +v.toPrecision(3) + ''; };

  class Plot {
    constructor(canvas, o) {
      this.cv = canvas; this.o = Object.assign({ xlabel: '', ylabel: '', xlog: false, ylog: false, xlim: [0, 1], ylim: [0, 1], title: '' }, o || {});
      this.dpr = Math.min(2, window.devicePixelRatio || 1);
    }
    resize() {
      const w = Math.max(200, this.cv.clientWidth || 300), hh = this.o.height || 220;
      if (this.cv.width !== w * this.dpr || this.cv.height !== hh * this.dpr) { this.cv.width = w * this.dpr; this.cv.height = hh * this.dpr; this.cv.style.height = hh + 'px'; }
      this.W = w; this.H = hh;
    }
    begin(opts) {
      Object.assign(this.o, opts || {});
      this.resize();
      const c = this.ctx = this.cv.getContext('2d'), o = this.o;
      c.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
      c.fillStyle = '#fff'; c.fillRect(0, 0, this.W, this.H);
      this.m = { l: 56, r: 12, t: o.title ? 24 : 12, b: 38 };
      const f = (v, lg) => (lg ? Math.log10(v) : v);
      this.sx = (x) => this.m.l + (f(x, o.xlog) - f(o.xlim[0], o.xlog)) / (f(o.xlim[1], o.xlog) - f(o.xlim[0], o.xlog)) * (this.W - this.m.l - this.m.r);
      this.sy = (y) => this.H - this.m.b - (f(y, o.ylog) - f(o.ylim[0], o.ylog)) / (f(o.ylim[1], o.ylog) - f(o.ylim[0], o.ylog)) * (this.H - this.m.t - this.m.b);
      c.font = '11px system-ui, sans-serif'; c.lineWidth = 1;
      const xt = o.xlog ? this.logTicks(o.xlim) : niceTicks(o.xlim[0], o.xlim[1], 6), yt = o.ylog ? this.logTicks(o.ylim) : niceTicks(o.ylim[0], o.ylim[1], 5);
      c.strokeStyle = '#e4e7ec'; c.fillStyle = '#4a5160';
      c.textAlign = 'center'; c.textBaseline = 'top';
      for (const v of xt) { const x = this.sx(v); c.beginPath(); c.moveTo(x, this.m.t); c.lineTo(x, this.H - this.m.b); c.stroke(); c.fillText(fmtTick(v), x, this.H - this.m.b + 4); }
      c.textAlign = 'right'; c.textBaseline = 'middle';
      for (const v of yt) { const y = this.sy(v); c.beginPath(); c.moveTo(this.m.l, y); c.lineTo(this.W - this.m.r, y); c.stroke(); c.fillText(fmtTick(v), this.m.l - 5, y); }
      c.strokeStyle = '#8a91a0'; c.strokeRect(this.m.l, this.m.t, this.W - this.m.l - this.m.r, this.H - this.m.t - this.m.b);
      c.fillStyle = '#1d2330'; c.textAlign = 'center'; c.textBaseline = 'alphabetic';
      c.fillText(o.xlabel, (this.m.l + this.W - this.m.r) / 2, this.H - 6);
      c.save(); c.translate(13, (this.m.t + this.H - this.m.b) / 2); c.rotate(-Math.PI / 2); c.fillText(o.ylabel, 0, 0); c.restore();
      if (o.title) {   // long Korean titles: shrink the font until the title fits the plot width
        let fs = 12; c.font = `600 ${fs}px system-ui, sans-serif`; c.textAlign = 'left';
        while (fs > 9 && c.measureText(o.title).width > this.W - this.m.l - 6) { fs--; c.font = `600 ${fs}px system-ui, sans-serif`; }
        c.fillText(o.title, this.m.l, 15);
      }
      c.save(); c.beginPath(); c.rect(this.m.l, this.m.t, this.W - this.m.l - this.m.r, this.H - this.m.t - this.m.b); c.clip(); this.clipped = true;
      return this;
    }
    logTicks(lim) { const out = []; for (let e = Math.ceil(Math.log10(lim[0]) - 1e-9); e <= Math.floor(Math.log10(lim[1]) + 1e-9); e++) out.push(Math.pow(10, e)); return out; }
    line(xs, ys, o) {
      o = Object.assign({ color: '#1f3b73', width: 2, dash: null }, o || {});
      const c = this.ctx; c.strokeStyle = o.color; c.lineWidth = o.width; c.setLineDash(o.dash || []); c.beginPath();
      let pen = false;
      for (let i = 0; i < xs.length; i++) {
        const x = xs[i], y = ys[i];
        if (!isFinite(x) || !isFinite(y) || (this.o.ylog && y <= 0) || (this.o.xlog && x <= 0)) { pen = false; continue; }
        const px = this.sx(x), py = this.sy(y);
        if (pen) c.lineTo(px, py); else c.moveTo(px, py);
        pen = true;
      }
      c.stroke(); c.setLineDash([]); return this;
    }
    vline(x, o) { o = Object.assign({ color: '#8a91a0', dash: [4, 3], width: 1.2 }, o || {}); const c = this.ctx; c.strokeStyle = o.color; c.lineWidth = o.width; c.setLineDash(o.dash); const px = this.sx(x); c.beginPath(); c.moveTo(px, this.m.t); c.lineTo(px, this.H - this.m.b); c.stroke(); c.setLineDash([]); return this; }
    hline(y, o) { o = Object.assign({ color: '#8a91a0', dash: [4, 3], width: 1.2 }, o || {}); const c = this.ctx; c.strokeStyle = o.color; c.lineWidth = o.width; c.setLineDash(o.dash); const py = this.sy(y); c.beginPath(); c.moveTo(this.m.l, py); c.lineTo(this.W - this.m.r, py); c.stroke(); c.setLineDash([]); return this; }
    band(x0, x1, color) { const c = this.ctx; c.fillStyle = color; const a = this.sx(Math.max(x0, this.o.xlim[0])), b = this.sx(Math.min(x1, this.o.xlim[1])); c.fillRect(a, this.m.t, b - a, this.H - this.m.t - this.m.b); return this; }
    marker(x, y, o) {
      o = Object.assign({ color: '#d73027', r: 5.5, label: '', dx: 8, dy: -8 }, o || {});
      if (!isFinite(x) || !isFinite(y) || (this.o.ylog && y <= 0)) return this;
      const c = this.ctx, px = this.sx(x), py = this.sy(y);
      c.fillStyle = o.color; c.strokeStyle = '#fff'; c.lineWidth = 1.5; c.beginPath(); c.arc(px, py, o.r, 0, 6.2832); c.fill(); c.stroke();
      if (o.label) { c.font = '600 11px system-ui'; c.fillStyle = o.color; c.textAlign = o.dx < 0 ? 'right' : 'left'; c.textBaseline = 'alphabetic'; c.fillText(o.label, px + o.dx, py + o.dy); }
      return this;
    }
    text(x, y, str, o) { o = Object.assign({ color: '#4a5160', align: 'left', font: '11px system-ui' }, o || {}); const c = this.ctx; c.fillStyle = o.color; c.font = o.font; c.textAlign = o.align; c.textBaseline = 'alphabetic'; c.fillText(str, this.sx(x), this.sy(y)); return this; }
    legend(items, pos) {
      const c = this.ctx; c.font = '11px system-ui'; let x = this.m.l + 8 + (pos === 'right' ? 0 : 0), y = this.m.t + 8;
      const wmax = Math.max(...items.map((it) => c.measureText(it.label).width)) + 34;
      if (pos === 'right') x = this.W - this.m.r - wmax - 4;
      c.fillStyle = 'rgba(255,255,255,0.85)'; c.fillRect(x - 4, y - 5, wmax + 6, items.length * 16 + 4);
      items.forEach((it, i) => { const yy = y + 5 + i * 16; c.strokeStyle = it.color; c.lineWidth = 2; c.setLineDash(it.dash || []); c.beginPath(); c.moveTo(x, yy); c.lineTo(x + 20, yy); c.stroke(); c.setLineDash([]); c.fillStyle = '#1d2330'; c.textAlign = 'left'; c.textBaseline = 'middle'; c.fillText(it.label, x + 26, yy); });
      return this;
    }
    end() { if (this.clipped) { this.ctx.restore(); this.clipped = false; } return this; }
  }

  // ---- visibility-aware animation loop shared by the widgets
  function animate(root, tick) {
    let raf = 0, visible = false, last = 0;
    const loop = (t) => { raf = 0; if (!visible) return; tick(t / 1000, (t - last) / 1000); last = t; raf = requestAnimationFrame(loop); };
    const reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
    const io = new IntersectionObserver((es) => { visible = es[0].isIntersecting; if (visible && !raf) raf = requestAnimationFrame(loop); });
    io.observe(root);
    tick(0, 0);
    return { reduce, redraw: () => tick(performance.now() / 1000, 0) };
  }

  const NS = 'http://www.w3.org/2000/svg';
  function svg(tag, attrs, ...kids) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs || {}) e.setAttribute(k, attrs[k]);
    for (const c of kids.flat()) if (c != null) e.append(c.nodeType ? c : document.createTextNode(c));
    return e;
  }

  G.UI = { h, svg, cmap, cmapRGB, shadeRGB, colorbar, slider, select, button, checkbox, Plot, animate, niceTicks };
})(typeof window !== 'undefined' ? window : globalThis);
