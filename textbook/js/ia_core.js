'use strict';
/* ia_core.js - widget scaffold shared by all lessons, and the three schematics (bench, resistor load, inverter). */
(function (G) {
  const { h, slider, select, button, checkbox, Plot, colorbar, animate } = G.UI;
  const MS = G.MS, { Scene } = G.Scene3D, clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const KP = 300e-6;

  const sgn = (v) => (v < 0 ? '−' : '');
  const fI = (I, d) => (Math.abs(I) < 1e-15 ? '0 A' : sgn(I) + MS.si(Math.abs(I), 'A', d || 3));
  const rows = (r) => '<dl class="ia-dl">' + r.map(([k, v, hint]) => `<dt>${k}</dt><dd>${v}${hint ? `<small>${hint}</small>` : ''}</dd>`).join('') + '</dl>';

  /**
   * makeWidget(root, spec):
   *  spec.controls: [{id,label,min,max,step,value,unit,log,fmt} | {type:'select',...} | {type:'check',...} | {type:'buttons',items:[{text,set:{id:v}}]} | {type:'play'}]
   *  spec.compute(vals, prev) -> state          spec.readout(state, vals) -> html
   *  spec.plots: [{h, draw(plot, state, vals)}]  spec.build3d(scene, state)   spec.schem(svgEl) -> {update(state)}
   *  spec.vrange(state) -> [vmin, vmax]          spec.onTick(dt, ctl, vals) -> true when state changed (animation)
   */
  function makeWidget(root, spec) {
    root.classList.add('ia');
    const vals = {}, ctl = {}, sliders = {};
    const ctlBox = h('div', { class: 'ia-ctls' }), read = h('div', { class: 'ia-read' });
    const c3d = h('canvas', { class: 'ia-cv' }), sv = h('svg', {});
    const svgEl = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svgEl.setAttribute('class', 'ia-svg');
    const plotCv = (spec.plots || []).map(() => h('canvas', { class: 'ia-cv' }));
    const cbar = colorbar(0, 1);
    const views = h('div', { class: 'ia-views' },
      h('div', { class: 'ia-card' }, c3d, h('div', { class: 'ia-cap', html: spec.cap3d || '3D 구조: 색 = 전위, 움직이는 점 = 전도 전류 (드래그로 회전, 더블클릭으로 복귀)' })),
      h('div', { class: 'ia-card' }, svgEl, h('div', { class: 'ia-cap', html: spec.capSchem || '회로도: 배선 색 = 노드 전압, 점의 방향·크기·속도 = 전류 (로그 스케일)' })),
      plotCv.map((c, i) => h('div', { class: 'ia-card' + (i === (spec.plots.length - 1) && spec.plots.length % 2 === 1 ? ' wide' : '') }, c)));
    const head = h('div', { class: 'ia-head' }, h('b', {}, '직접 조작해 보기'), h('span', { class: 'ia-note', html: spec.note || '' }));
    root.append(head, h('div', { class: 'ia-grid' }, h('div', { class: 'ia-side' }, ctlBox, read), views),
      h('div', { class: 'ia-foot' }, h('span', {}, '전위 색:'), cbar, h('span', { class: 'ia-fine', html: spec.foot || '' })));

    let state = null, phase = 0, playing = false, last = 0;
    const scene = new Scene(c3d, spec.scene || {}), schem = spec.schem ? spec.schem(svgEl) : null;
    const plots = plotCv.map((c, i) => new Plot(c, { height: spec.plots[i].h || 210 }));
    const get = () => { for (const id in ctl) vals[id] = ctl[id].get(); return vals; };
    const refresh = () => {
      get(); state = spec.compute(vals, state);
      const [a, b] = spec.vrange ? spec.vrange(state, vals) : [0, 1]; state.vmin = a; state.vmax = b; cbar.update(a, b);
      read.innerHTML = spec.readout(state, vals);
      plots.forEach((p, i) => spec.plots[i].draw(p, state, vals));
      draw();
    };
    const draw = () => {
      if (!state) return;
      scene.reset(); state.phase = phase; spec.build3d(scene, state); scene.render();
      if (schem) { schem.update(state); schem.s.tick(phase); }
    };
    scene.onView = draw;
    // controls
    for (const c of spec.controls) {
      if (c.type === 'select') { const s = select(Object.assign({ onInput: refresh }, c)); ctl[c.id] = s; ctlBox.append(s.el); }
      else if (c.type === 'check') { const s = checkbox(Object.assign({ onInput: refresh }, c)); ctl[c.id] = s; ctlBox.append(s.el); }
      else if (c.type === 'buttons') {
        ctlBox.append(h('div', { class: 'ia-btns' }, c.items.map((it) => button(it.text, () => { for (const k in it.set) { if (sliders[k]) sliders[k].set(it.set[k]); else if (ctl[k]) ctl[k].set(it.set[k]); } refresh(); }))));
      } else if (c.type === 'play') {
        const b = button('▶ 재생', () => { playing = !playing; b.textContent = playing ? '⏸ 정지' : '▶ 재생'; }); ctl[c.id] = { get: () => playing, set: () => {} }; ctlBox.append(b);
      } else { const s = slider(Object.assign({ onInput: refresh }, c)); ctl[c.id] = s; sliders[c.id] = s; ctlBox.append(s.el); }
    }
    // URL presets: ?ia-l1=vgs:1.2,vds:0.5
    const q = new URLSearchParams(location.search).get('ia-' + root.id.replace(/^ia-/, ''));
    if (q) for (const kv of q.split(',')) { const [k, v] = kv.split(':'); if (sliders[k]) sliders[k].set(+v); else if (ctl[k]) ctl[k].set(v); }
    const reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
    const loop = animate(root, (t, dt) => {
      if (!state) return;
      if (playing && spec.onTick && dt > 0) { const changed = spec.onTick(Math.min(dt, 0.1), ctl, get()); if (changed) refresh(); }
      phase = reduce ? 0 : t; draw();
    });
    new ResizeObserver(() => { if (state) { plots.forEach((p, i) => spec.plots[i].draw(p, state, vals)); draw(); } }).observe(root);
    refresh();
    root.__ia = { ctl, refresh, get: () => state };
    return root.__ia;
  }

  // ------------------------------------------------------------------ schematics
  const VW = 380;
  /** bench: Vgs and Vds sources around one MOSFET. update({vgs, vds, id, vmin, vmax, mult, caps}) */
  function benchSchem(svgEl, o) {
    o = o || {};
    const s = new G.Schem(svgEl, VW, 270), m = s.mos(170, 130, { size: 20, label: o.label || 'M1' });
    const wg = s.wire([[93, 130], [170, 130]]), wgnd = s.wire([[80, 143], [80, 205]]), wd = s.wire([[300, 117], [300, 62], [202, 62], [202, 102]]), ws = s.wire([[202, 158], [202, 205], [300, 205], [300, 143]]);
    s.vsource(80, 130, 'Vgs', { side: 'left' }); s.vsource(300, 130, 'Vds'); s.ground(80, 205); s.ground(251, 205); s.dot(202, 205);
    const bg = s.badge(8, 112, 'G'), bd = s.badge(212, 52, 'D'), bs = s.badge(214, 198, 'S');
    const tI = s.text(212, 86, '', { color: '#b03a00', size: 12 }), tI2 = s.text(212, 100, '', { color: '#b03a00', size: 10, weight: 500 }), tG = s.text(100, 150, 'Ig = 0', { size: 10, weight: 500, color: '#4a5160' }), tM = s.text(m.top[0] + 6, 168, '', { size: 10, weight: 600, color: '#4a5160' });
    let capG = null;
    if (o.caps) {   // dashed intrinsic capacitances between gate and drain / source (lesson 6)
      s.line(170, 130, 170, 88, { color: '#b03a00', dash: '4 3', width: 1.6 }); s.line(170, 88, 150, 88, { color: '#b03a00', dash: '4 3', width: 1.6 });
      capG = { gd: s.text(98, 70, '', { color: '#b03a00', size: 11 }), gs: s.text(98, 196, '', { color: '#b03a00', size: 11 }) };
      s.line(170, 130, 170, 172, { color: '#b03a00', dash: '4 3', width: 1.6 });
      s.capacitor(150, 70, 100, '', { color: '#b03a00' }); s.capacitor(150, 160, 190, '', { color: '#b03a00' });
      s.line(150, 100, 150, 130, { color: '#b03a00', dash: '4 3', width: 1.6 });
    }
    return { s, update(st) {
      const { vmin, vmax } = st;
      wg.set(st.vgs, 0, vmin, vmax); wgnd.set(0, 0, vmin, vmax); wd.set(st.vds, st.id, vmin, vmax); ws.set(0, st.id, vmin, vmax);
      bg.set(st.vgs, vmin, vmax); bd.set(st.vds, vmin, vmax); bs.set(0, vmin, vmax);
      tI.textContent = `Id = ${fI(st.id)}`; tI2.textContent = st.mult ? `(1개당 ${fI(st.id / st.mult)})` : ''; tM.textContent = st.mlabel || '';
      if (capG) { capG.gd.textContent = `Cgd ${(st.cgd * 1e15).toFixed(2)} fF`; capG.gs.textContent = `Cgs ${(st.cgs * 1e15).toFixed(2)} fF`; }
    } };
  }

  /** NMOS with drain resistor to Vdd (+ optional load capacitor). update({vdd, vg, vd, iR, iD, iC}) */
  function rdSchem(svgEl, o) {
    o = o || {};
    const s = new G.Schem(svgEl, VW, 290), m = s.mos(178, 190, { size: 20, label: 'M1' });
    const wRail = s.wire([[160, 22], [210, 22]], { width: 3.6 }), wRt = s.wire([[210, 22], [210, 52]]), wRb = s.wire([[210, 104], [210, 134]]), wRbody = s.wire([[210, 52], [210, 104]], { width: 0.1 });
    s.resistor(210, 52, 104, ''); s.text(196, 82, 'Rd', { size: 11, anchor: 'end' }); wRbody.path.setAttribute('stroke', 'none');
    const wD = s.wire([[210, 134], [210, 162]]), wS = s.wire([[210, 218], [210, 252]]), wG = s.wire([[103, 190], [178, 190]]), wGg = s.wire([[90, 203], [90, 252]]);
    s.vsource(90, 190, 'Vg', { side: 'left' }); s.ground(90, 252); s.ground(210, 252); s.dot(210, 134);
    let wC1, wC2, wC3, tC;
    if (o.cap) { wC1 = s.wire([[210, 134], [310, 134], [310, 168]]); wC3 = s.wire([[310, 168], [310, 178]], { width: 0.1 }); wC2 = s.wire([[310, 208], [310, 252]]); s.capacitor(310, 168, 208, 'CL'); s.ground(310, 252); wC3.path.setAttribute('stroke', 'none'); tC = s.text(302, 244, '', { color: '#b03a00', size: 11, anchor: 'end' }); }
    const bRail = s.badge(222, 18, 'Vdd'), bD = s.badge(222, 128, 'Vd'), bG = s.badge(8, 172, 'Vg');
    const tR = s.text(224, 76, '', { color: '#b03a00', size: 11 }), tD = s.text(222, 156, '', { color: '#b03a00', size: 11 }), tK = s.text(8, 284, '', { size: 11, weight: 500, color: '#4a5160' });
    return { s, update(st) {
      const { vmin, vmax } = st;
      wRail.set(st.vdd, 0, vmin, vmax); wRt.set(st.vdd, st.iR, vmin, vmax); wRbody.set(null, st.iR, vmin, vmax); wRb.set(st.vd, st.iR - (st.iC || 0) * 0, vmin, vmax);
      wRb.I = st.iR; wD.set(st.vd, st.iD, vmin, vmax); wS.set(0, st.iD, vmin, vmax); wG.set(st.vg, 0, vmin, vmax); wGg.set(0, 0, vmin, vmax);
      if (wC1) { wC1.set(st.vd, st.iC, vmin, vmax); wC2.set(0, st.iC, vmin, vmax); wC3.I = st.iC; tC.textContent = `iC = ${fI(st.iC)}`; }
      bRail.set(st.vdd, vmin, vmax); bD.set(st.vd, vmin, vmax); bG.set(st.vg, vmin, vmax);
      tR.textContent = `iR = ${fI(st.iR)}`; tD.textContent = `iD = ${fI(st.iD)}`; tK.textContent = st.kclText || '';
    } };
  }

  /** CMOS inverter with load capacitor. update({vdd, vin, vout, ip, in_, ic}) ; ip = current from Vdd through the PMOS, in_ = through the NMOS */
  function invSchem(svgEl) {
    const s = new G.Schem(svgEl, VW, 300), p = s.mos(150, 98, { size: 20, p: true, label: 'M2' }), n = s.mos(150, 208, { size: 20, label: 'M1' });
    const wRail = s.wire([[160, 18], [215, 18]], { width: 3.6 }), wP1 = s.wire([[182, 18], [182, 70]]), wP2 = s.wire([[182, 126], [182, 154]]), wN1 = s.wire([[182, 154], [182, 180]]), wN2 = s.wire([[182, 236], [182, 268]]);
    const wIn = s.wire([[73, 154], [110, 154]]), wG = s.wire([[110, 98], [110, 208]]), wGp = s.wire([[110, 98], [144, 98]]), wGn = s.wire([[110, 208], [150, 208]]), wInG = s.wire([[60, 167], [60, 268]]);
    const wO = s.wire([[182, 154], [290, 154]]), wC1 = s.wire([[290, 154], [290, 190]]), wC2 = s.wire([[290, 222], [290, 268]]), wCb = s.wire([[290, 190], [290, 222]], { width: 0.1 });
    s.vsource(60, 154, 'Vin', { side: 'left' }); s.capacitor(290, 190, 222, 'CL'); s.ground(60, 268); s.ground(182, 268); s.ground(290, 268); s.dot(110, 154); s.dot(182, 154); wCb.path.setAttribute('stroke', 'none');
    const bV = s.badge(194, 14, 'Vdd'), bI = s.badge(8, 138, 'in'), bO = s.badge(296, 150, 'out');
    const tP = s.text(194, 84, '', { color: '#b03a00', size: 11 }), tN = s.text(194, 200, '', { color: '#b03a00', size: 11 }), tC = s.text(300, 212, '', { color: '#b03a00', size: 11 });
    return { s, update(st) {
      const { vmin, vmax } = st;
      wRail.set(st.vdd, 0, vmin, vmax); wP1.set(st.vdd, st.ip, vmin, vmax); wP2.set(st.vout, st.ip, vmin, vmax); wN1.set(st.vout, st.in_, vmin, vmax); wN2.set(0, st.in_, vmin, vmax);
      wIn.set(st.vin, 0, vmin, vmax); wG.set(st.vin, 0, vmin, vmax); wGp.set(st.vin, 0, vmin, vmax); wGn.set(st.vin, 0, vmin, vmax); wInG.set(0, 0, vmin, vmax);
      wO.set(st.vout, 0, vmin, vmax); wC1.set(st.vout, st.ic || 0, vmin, vmax); wC2.set(0, st.ic || 0, vmin, vmax); wCb.I = st.ic || 0;
      bV.set(st.vdd, vmin, vmax); bI.set(st.vin, vmin, vmax); bO.set(st.vout, vmin, vmax);
      tP.textContent = `Isd(PMOS) = ${fI(st.ip)}`; tN.textContent = `Id(NMOS) = ${fI(st.in_)}`; tC.textContent = st.ic !== undefined ? `iC = ${fI(st.ic)}` : '';
    } };
  }

  G.IA = { makeWidget, benchSchem, rdSchem, invSchem, fI, rows, KP, clamp, W: {} };
})(typeof window !== 'undefined' ? window : globalThis);
