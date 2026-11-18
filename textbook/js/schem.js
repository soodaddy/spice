'use strict';
/* schem.js - SVG circuit schematics: wires coloured by node voltage, moving dots for current (direction and log-scaled size). */
(function (G) {
  const { svg, cmap } = G.UI;
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const INK = '#1f3b73', HOT = '#b03a00';
  const mag = (I) => clamp((Math.log10(Math.max(Math.abs(I), 1e-13)) + 10) / 7, 0, 1);

  class Schem {
    constructor(el, w, h) {
      this.el = el; this.w = w; this.h = h; el.setAttribute('viewBox', `0 0 ${w} ${h}`); el.setAttribute('preserveAspectRatio', 'xMidYMid meet');
      el.style.aspectRatio = `${w} / ${h}`;
      this.g0 = svg('g', {}); this.g1 = svg('g', {}); this.g2 = svg('g', {}); el.append(svg('rect', { x: 0, y: 0, width: w, height: h, fill: '#fff' }), this.g0, this.g1, this.g2);
      this.wires = [];
    }
    /** polyline wire; set(v, I, vmin, vmax) colours it and sets the current (positive = along the point order) */
    wire(pts, o) {
      o = o || {};
      const d = pts.map((p, i) => (i ? 'L' : 'M') + p[0] + ' ' + p[1]).join(' ');
      const wd = o.width || 3.2;
      if (wd > 1) this.g0.append(svg('path', { d, fill: 'none', 'stroke-width': wd + 2.2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round', stroke: '#33405c' }));   // dark outline: pale colours stay visible
      const path = svg('path', { d, fill: 'none', 'stroke-width': wd, 'stroke-linejoin': 'round', 'stroke-linecap': 'round', stroke: '#888' });
      this.g0.append(path);
      const seg = []; let tot = 0;
      for (let i = 1; i < pts.length; i++) { const l = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); seg.push(l); tot += l; }
      const w = { pts, seg, len: tot, path, dots: [], I: 0, spacing: o.spacing || 15,
        set: (v, I, vmin, vmax) => { path.setAttribute('stroke', v === null ? '#888' : cmap((v - vmin) / ((vmax - vmin) || 1))); w.I = I || 0; } };
      this.wires.push(w); return w;
    }
    at(w, s) { // point at distance s along the wire
      let acc = 0;
      for (let i = 0; i < w.seg.length; i++) { if (s <= acc + w.seg[i] || i === w.seg.length - 1) { const f = w.seg[i] ? (s - acc) / w.seg[i] : 0, a = w.pts[i], b = w.pts[i + 1]; return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f]; } acc += w.seg[i]; }
      return w.pts[0];
    }
    tick(phase) {
      for (const w of this.wires) {
        const on = Math.abs(w.I) > 1e-12 && w.len > 1, m = mag(w.I), n = on ? Math.max(1, Math.floor(w.len / w.spacing)) : 0;
        while (w.dots.length < n) { const c = svg('circle', { r: 3, fill: '#fff', stroke: '#222', 'stroke-width': 1 }); this.g2.append(c); w.dots.push(c); }
        while (w.dots.length > n) w.dots.pop().remove();
        const speed = 14 + 130 * m, r = 2 + 2.4 * m, dir = w.I >= 0 ? 1 : -1, sp = w.len / Math.max(1, n);
        w.dots.forEach((c, i) => {
          const s = (((i * sp + dir * phase * speed) % w.len) + w.len) % w.len, p = this.at(w, s);
          c.setAttribute('cx', p[0].toFixed(1)); c.setAttribute('cy', p[1].toFixed(1)); c.setAttribute('r', r.toFixed(1)); c.setAttribute('fill', w.I >= 0 ? '#fff7d6' : '#d6f0ff');
        });
      }
    }
    text(x, y, str, o) {
      o = o || {};
      const t = svg('text', { x, y, 'font-size': o.size || 12, 'font-family': 'system-ui, sans-serif', 'font-weight': o.weight || 600, fill: o.color || INK, 'text-anchor': o.anchor || 'start', 'paint-order': 'stroke', stroke: '#fff', 'stroke-width': 3 }, str);
      this.g1.append(t); return t;
    }
    line(x0, y0, x1, y1, o) { o = o || {}; const l = svg('line', { x1: x0, y1: y0, x2: x1, y2: y1, stroke: o.color || INK, 'stroke-width': o.width || 2, 'stroke-linecap': 'round', 'stroke-dasharray': o.dash || '' }); this.g1.append(l); return l; }
    dot(x, y, r) { const c = svg('circle', { cx: x, cy: y, r: r || 3.2, fill: INK }); this.g1.append(c); return c; }
    /** MOSFET symbol, gate plate at x; returns terminal anchors. pmos: bubble on the gate, source on top. */
    mos(x, y, o) {
      o = o || {}; const s = o.size || 18, p = !!o.p;
      this.line(x, y - 0.8 * s, x, y + 0.8 * s, { width: 3 }); this.line(x + 0.6 * s, y - 1.0 * s, x + 0.6 * s, y + 1.0 * s, { width: 3 });
      this.line(x + 0.6 * s, y - 0.7 * s, x + 1.6 * s, y - 0.7 * s); this.line(x + 0.6 * s, y + 0.7 * s, x + 1.6 * s, y + 0.7 * s); this.line(x + 0.6 * s, y, x + 1.6 * s, y, { width: 1 });
      if (p) this.g1.append(svg('circle', { cx: x - 0.16 * s, cy: y, r: 0.15 * s, fill: '#fff', stroke: INK, 'stroke-width': 1.6 }));
      const top = [x + 1.6 * s, y - 1.4 * s], bot = [x + 1.6 * s, y + 1.4 * s];
      this.line(top[0], y - 0.7 * s, top[0], top[1]); this.line(bot[0], y + 0.7 * s, bot[0], bot[1]);
      if (o.label) this.text(x + 2.0 * s, y + 4, o.label, { size: 11, weight: 600 });
      return { g: [x - (p ? 0.31 * s : 0), y], top, bot, mid: [x + 1.6 * s, y] };
    }
    resistor(x, y0, y1, label) {   // vertical zig-zag, y0 < y1 ; wires are drawn by the caller up to y0 and from y1
      const n = 6, a = y0 + (y1 - y0) * 0.2, b = y1 - (y1 - y0) * 0.2, pts = [[x, a]];
      for (let i = 0; i < 2 * n; i++) pts.push([x + (i % 2 ? 7 : -7), a + (b - a) * (i + 0.5) / (2 * n)]);
      pts.push([x, b]);
      this.g1.append(svg('polyline', { points: pts.map((p) => p.join(',')).join(' '), fill: 'none', stroke: INK, 'stroke-width': 2, 'stroke-linejoin': 'round' }));
      if (label) this.text(x + 12, (y0 + y1) / 2 + 4, label, { size: 11 });
      return { top: [x, y0], bot: [x, y1], a, b };
    }
    capacitor(x, yTop, yBot, label, o) {
      o = o || {}; const m = (yTop + yBot) / 2, col = o.color || INK;
      this.line(x, yTop, x, m - 4, { color: col, dash: o.dash }); this.line(x, m + 4, x, yBot, { color: col, dash: o.dash });
      this.line(x - 10, m - 4, x + 10, m - 4, { width: 3, color: col }); this.line(x - 10, m + 4, x + 10, m + 4, { width: 3, color: col });
      if (label) this.text(x + 14, m + 4, label, { size: 11, color: o.labelColor || INK });
    }
    vsource(x, y, label, o) {
      o = o || {}; const r = 13;
      this.g1.append(svg('circle', { cx: x, cy: y, r, fill: '#fff', stroke: INK, 'stroke-width': 2 }));
      this.text(x, y - 1, '+', { size: 12, anchor: 'middle', weight: 700 }); this.text(x, y + 11, '−', { size: 12, anchor: 'middle', weight: 700 });
      if (label) this.text(x + (o.side === 'left' ? -r - 6 : r + 6), y + 4, label, { color: HOT, anchor: o.side === 'left' ? 'end' : 'start', size: 11 });
    }
    ground(x, y) { this.line(x, y, x, y + 6); this.line(x - 11, y + 6, x + 11, y + 6, { width: 2.4 }); this.line(x - 7, y + 10, x + 7, y + 10, { width: 2.4 }); this.line(x - 3, y + 14, x + 3, y + 14, { width: 2.4 }); }
    /** coloured rounded badge showing a node voltage; returns {set(v, vmin, vmax)} */
    badge(x, y, name) {
      const g = svg('g', {}), r = svg('rect', { x: x - 3, y: y - 12, width: 74, height: 17, rx: 8, fill: '#ddd', stroke: '#555', 'stroke-width': 0.8 }), t = svg('text', { x: x + 34, y: y + 1, 'font-size': 11, 'font-family': 'system-ui, sans-serif', 'font-weight': 700, 'text-anchor': 'middle', fill: '#111' });
      g.append(r, t); this.g1.append(g);
      return { set: (v, vmin, vmax, extra) => { const k = (v - vmin) / ((vmax - vmin) || 1); r.setAttribute('fill', cmap(k)); t.textContent = `${name} ${v.toFixed(2)} V${extra || ''}`; t.setAttribute('fill', k > 0.82 || k < 0.12 ? '#fff' : '#111'); } };
    }
  }
  G.Schem = Schem; G.SchemMag = mag;
})(typeof window !== 'undefined' ? window : globalThis);
