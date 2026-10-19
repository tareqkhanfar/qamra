"""Scripts the renderer runs in the page before printing (browser JavaScript, kept out of render.py).

- `FIT_JS`: every story text container shrinks to fit and keeps its words off the faces in the picture.
- `SHAPES_JS`: the painted watercolor wash under the text, drawn once the text is fitted.
"""

# Shrink-to-fit for every text container ([data-panel] holding .story-text): all its texts shrink together
# in 0.5 pt steps down to the age minimum (then the lines tighten to 1.8, never less) until they fit and stay
# off every face in the picture (the page's data-faces, from `qamra_ai.pipeline.art_faces`). Still on a face:
# the text narrows and slides to one side of its band, then tries the layout's other bands (data-area); the
# first clear placement wins, else it stays and reports `face` (the page goes to review). `fill` is how much
# of the container's content box the text uses; `moved` names the placement it took.
FIT_JS = """
(minPt) => {
  const out = [];
  // computed sizes are CSS px (16 pt = 21.333… px): round to 0.01 pt so an unshrunk size compares equal
  const ptOf = el => Math.round(parseFloat(getComputedStyle(el).fontSize) * 75) / 100;
  for (const box of document.querySelectorAll('[data-panel]')) {
    const texts = [...box.querySelectorAll('.story-text')];
    if (!texts.length) continue;
    // in-flow content only: decorative shapes (absolute) may spill out of the box on purpose
    const flow = [...box.children].filter(c => {
      const st = getComputedStyle(c);
      return st.position !== 'absolute' && st.display !== 'none';
    });
    const measure = () => {
      const cs = getComputedStyle(box);
      const inner = box.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
      const gap = (parseFloat(cs.rowGap) || 0) * Math.max(0, flow.length - 1);
      const used = flow.reduce((a, c) => {
        const st = getComputedStyle(c);
        return a + c.getBoundingClientRect().height + parseFloat(st.marginTop) + parseFloat(st.marginBottom);
      }, gap);
      return {inner, used};
    };
    const over = () => {
      const {inner, used} = measure();
      return used > inner + 1 || texts.some(t => t.scrollWidth > t.clientWidth + 1);
    };
    // faces in the picture (data-faces on the page, fractions of the image) in page pixels, grown a little
    // for hair and chin; the text (or its painted shape) must stay off them
    const faces = (() => {
      const sec = box.closest('section'), img = sec && sec.querySelector('img.bleed-img');
      if (!img || !sec.dataset.faces || !img.naturalWidth) return [];
      const r = img.getBoundingClientRect();
      const k = Math.max(r.width / img.naturalWidth, r.height / img.naturalHeight);
      const dw = img.naturalWidth * k, dh = img.naturalHeight * k;
      const ox = r.left + (r.width - dw) / 2, oy = r.top + (r.height - dh) / 2;
      return sec.dataset.faces.split(';').map(f => f.split(' ').map(Number)).map(([x0, y0, x1, y1]) => {
        const gx = (x1 - x0) * .05, gy = (y1 - y0) * .1;
        return [ox + (x0 - gx) * dw, oy + (y0 - gy) * dh, ox + (x1 + gx) * dw, oy + (y1 + gy) * dh];
      });
    })();
    const MM = 96 / 25.4;
    const guard = () => {  // a painted shape spreads ~3 mm past its box; a fade only matters where the words are
      const rects = box.dataset.guard === 'text' ? texts.map(t => t.getBoundingClientRect()) : [box.getBoundingClientRect()];
      const g = 2 * MM;
      return rects.map(r => [r.left - g, r.top - g, r.right + g, r.bottom + g]);
    };
    const onFace = () => guard().some(([a, b, c, d]) => faces.some(([x0, y0, x1, y1]) => a < x1 && c > x0 && b < y1 && d > y0));
    const start = texts.map(ptOf);
    let pts = start;
    const fit = () => {  // shrink in 0.5 pt steps to the age minimum, then tighten the lines to 1.8 (never less)
      pts = start;
      texts.forEach((t, i) => { t.style.fontSize = pts[i] + 'pt'; t.style.lineHeight = ''; });
      while ((over() || onFace()) && Math.max(...pts) > minPt) {
        pts = pts.map(p => Math.max(minPt, p - 0.5));
        texts.forEach((t, i) => { t.style.fontSize = pts[i] + 'pt'; });
      }
      if ((over() || onFace()) && texts.every(t => parseFloat(getComputedStyle(t).lineHeight) / parseFloat(getComputedStyle(t).fontSize) > 1.81)) {
        texts.forEach(t => { t.style.lineHeight = '1.8'; });
      }
    };
    fit();
    // still on a face: first narrow the text and slide it to one side of its band (the calm sky beside a
    // head), then try the other bands the layout knows (a side text to the top or bottom, top ↔ bottom);
    // keep the first placement that is clear, else stay where the theme put it
    const area = box.dataset.area;
    let moved = '';
    const narrow = (mw, side) => {
      const safe = getComputedStyle(document.documentElement).getPropertyValue('--safe').trim() || '13mm';
      if (box.dataset.guard === 'text') {  // a fade band: the words narrow inside it
        texts.forEach(t => { t.style.maxWidth = mw; t.style.marginLeft = side === 'left' ? '0' : 'auto';
                             t.style.marginRight = side === 'right' ? '0' : 'auto'; });
      } else {
        box.style.maxWidth = mw; box.style.margin = '0'; box.style.maxHeight = '150mm';
        box.style.left = side === 'left' ? `calc(${safe} + 2mm)` : 'auto';
        box.style.right = side === 'right' ? `calc(${safe} + 2mm)` : 'auto';
      }
    };
    const reset = () => {
      texts.forEach(t => { t.style.maxWidth = ''; t.style.marginLeft = ''; t.style.marginRight = ''; });
      for (const k of ['maxWidth', 'maxHeight', 'margin', 'left', 'right']) box.style[k] = '';
    };
    if (onFace() && area && faces.length) {
      const tries = [];
      if (area === 'top' || area === 'bottom') {
        for (const mw of ['140mm', '124mm', '108mm', '92mm']) for (const side of ['left', 'right']) tries.push([area, mw, side]);
      }
      const others = {left: ['top', 'bottom'], right: ['top', 'bottom'], top: ['bottom'], bottom: ['top']}[area] || [];
      for (const alt of others) {
        tries.push([alt, '', '']);
        for (const mw of ['140mm', '124mm', '108mm', '92mm']) for (const side of ['left', 'right']) tries.push([alt, mw, side]);
      }
      for (const [alt, mw, side] of tries) {
        box.classList.replace(area, alt);
        if (mw) narrow(mw, side);
        fit();
        if (!onFace() && !over()) { moved = alt + (side ? '-' + side : ''); break; }
        reset();
        box.classList.replace(alt, area);
      }
      if (!moved) fit();
    }
    const {inner, used} = measure();
    out.push({page: Number(box.dataset.panel), pt: Math.min(...pts), overflow: over(), face: onFace(), moved,
              fill: inner > 0 ? Math.round(used / inner * 1000) / 1000 : 1});
  }
  return out;
}
"""

# The painted watercolor wash under story text set on the art, drawn in the browser once the text is fitted.
#
# Every `.ink-shape[data-shape="wash"]` (an empty layer inside a text container) gets an SVG blob that hugs the
# container's final size: a rounded outline whose edge wanders (seeded waves, so a page always draws the same
# shape and the pages differ), painted by an SVG filter: a ragged edge (noise displacement), uneven pigment
# (large-scale mottling that never drops below about 80% of the wash), a darker drying edge and fine
# granulation. Colors are CSS variables set on the page from the picture's palette (`checks.palette_for`):
# --wash, --deep and --o (the wash's opacity: higher over busy art).
#
# The filtered blob is rasterized by Chromium at print resolution; the outline and every letter stay vector.
# `checks.palette_for` measures the words' contrast on the wash at 80% of --o, the thinnest it gets.
SHAPES_JS = r"""
() => {
  const MM = 96 / 25.4;
  const NS = 'http://www.w3.org/2000/svg';
  const rng = seed => { let s = (seed * 2654435761) >>> 0 || 1;
    return () => (s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296; };
  // a point at arc length t along a rounded rectangle (x0, y0, w, h, radius r), with its outward normal
  const along = (x0, y0, w, h, r, t) => {
    const L = [w - 2 * r, Math.PI * r / 2, h - 2 * r, Math.PI * r / 2, w - 2 * r, Math.PI * r / 2, h - 2 * r, Math.PI * r / 2];
    let i = 0; while (i < 7 && t > L[i]) { t -= L[i]; i++; }
    const arc = (cx, cy, a0) => { const a = a0 + t / r; return [cx + r * Math.cos(a), cy + r * Math.sin(a), Math.cos(a), Math.sin(a)]; };
    switch (i) {
      case 0: return [x0 + r + t, y0, 0, -1];
      case 1: return arc(x0 + w - r, y0 + r, -Math.PI / 2);
      case 2: return [x0 + w, y0 + r + t, 1, 0];
      case 3: return arc(x0 + w - r, y0 + h - r, 0);
      case 4: return [x0 + w - r - t, y0 + h, 0, 1];
      case 5: return arc(x0 + r, y0 + h - r, Math.PI / 2);
      case 6: return [x0, y0 + h - r - t, -1, 0];
      default: return arc(x0 + r, y0 + r, Math.PI);
    }
  };
  // the outline: the rounded rectangle grown by `pad`, its edge pushed in and out by smooth waves (`amp`)
  const outline = (w, h, o) => {
    const rand = rng(o.seed);
    const x0 = -o.pad, y0 = -o.pad, W = w + 2 * o.pad, H = h + 2 * o.pad;
    const r = Math.min(o.r, W / 2 - 1, H / 2 - 1);
    const per = 2 * (W + H - 4 * r) + 2 * Math.PI * r;
    const n = Math.max(28, Math.round(per / o.step));
    const waves = [[2 + Math.floor(rand() * 2), rand() * 6.3, .55], [5 + Math.floor(rand() * 3), rand() * 6.3, .3],
                   [11 + Math.floor(rand() * 5), rand() * 6.3, .15]];
    const pts = [];
    for (let i = 0; i < n; i++) {
      const [x, y, nx, ny] = along(x0, y0, W, H, r, per * i / n);
      let d = 0; for (const [f, ph, a] of waves) d += a * Math.sin(2 * Math.PI * f * i / n + ph);
      d = o.amp * d;
      pts.push([x + nx * d, y + ny * d]);
    }
    return pts;
  };
  const smooth = pts => {  // closed Catmull-Rom → cubic Béziers
    const n = pts.length, f = v => v.toFixed(2);
    let d = `M${f(pts[0][0])} ${f(pts[0][1])}`;
    for (let i = 0; i < n; i++) {
      const p0 = pts[(i - 1 + n) % n], p1 = pts[i], p2 = pts[(i + 1) % n], p3 = pts[(i + 2) % n];
      d += `C${f(p1[0] + (p2[0] - p0[0]) / 6)} ${f(p1[1] + (p2[1] - p0[1]) / 6)} ${f(p2[0] - (p3[0] - p1[0]) / 6)} ${f(p2[1] - (p3[1] - p1[1]) / 6)} ${f(p2[0])} ${f(p2[1])}`;
    }
    return d + 'Z';
  };
  const el = (tag, attrs) => { const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v); return e; };

  for (const host of document.querySelectorAll('.ink-shape[data-shape]')) {
    host.replaceChildren();
    const box = host.getBoundingClientRect();
    const w = box.width, h = box.height;
    if (w < 4 || h < 4) continue;
    const kind = host.dataset.shape, seed = Number(host.dataset.seed || 1);
    const cs = getComputedStyle(host);
    const v = name => cs.getPropertyValue(name).trim();
    const o = parseFloat(v('--o')) || .9;
    const M = 12 * MM;
    const svg = el('svg', {viewBox: `${-M} ${-M} ${w + 2 * M} ${h + 2 * M}`, 'aria-hidden': 'true'});
    svg.style.cssText = `position:absolute;left:${-M}px;top:${-M}px;width:${w + 2 * M}px;height:${h + 2 * M}px;overflow:visible`;
    if (kind === 'wash') {
      // One soft blob, painted by an SVG filter: a ragged edge (noise displacement), uneven pigment
      // (large-scale mottling, never below 80% of the wash), a darker drying edge and fine granulation.
      const r = Math.min(18 * MM, h * .45);
      const body = outline(w, h, {seed: seed * 7 + 2, pad: 2.6 * MM, r: r, amp: 2.4 * MM, step: 5 * MM});
      const id = `wc-${seed}-${Math.round(w)}`;
      const f = el('filter', {id, x: '-15%', y: '-15%', width: '130%', height: '130%', 'color-interpolation-filters': 'sRGB'});
      const add = (tag, attrs) => { const e = el(tag, attrs); f.append(e); return e; };
      add('feTurbulence', {type: 'fractalNoise', baseFrequency: (0.09 / MM).toFixed(4), numOctaves: 3, seed: seed % 97 + 1, result: 'edgeNoise'});
      add('feDisplacementMap', {in: 'SourceGraphic', in2: 'edgeNoise', scale: (3.4 * MM).toFixed(1), xChannelSelector: 'R', yChannelSelector: 'G', result: 'shape'});
      add('feTurbulence', {type: 'fractalNoise', baseFrequency: (0.022 / MM).toFixed(4), numOctaves: 2, seed: seed % 89 + 7, result: 'mottleNoise'});
      add('feColorMatrix', {in: 'mottleNoise', type: 'matrix', values: '0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -0.32 1.12', result: 'mottle'});
      add('feComposite', {in: 'shape', in2: 'mottle', operator: 'in', result: 'paint'});
      add('feMorphology', {in: 'shape', operator: 'erode', radius: (1.1 * MM).toFixed(1), result: 'inner'});
      add('feComposite', {in: 'shape', in2: 'inner', operator: 'out', result: 'rimRaw'});
      add('feGaussianBlur', {in: 'rimRaw', stdDeviation: (.45 * MM).toFixed(2), result: 'rimSoft'});
      add('feFlood', {'flood-color': v('--deep'), 'flood-opacity': '.42', result: 'rimInk'});
      add('feComposite', {in: 'rimInk', in2: 'rimSoft', operator: 'in', result: 'rim'});
      add('feComposite', {in: 'rim', in2: 'shape', operator: 'in', result: 'rimIn'});
      add('feTurbulence', {type: 'fractalNoise', baseFrequency: (0.9 / MM).toFixed(3), numOctaves: 1, seed: seed % 83 + 3, result: 'grainNoise'});
      add('feColorMatrix', {in: 'grainNoise', type: 'matrix', values: '0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -2.2 1.1', result: 'grainMask'});
      add('feFlood', {'flood-color': v('--deep'), 'flood-opacity': '.08', result: 'grainInk'});
      add('feComposite', {in: 'grainInk', in2: 'grainMask', operator: 'in', result: 'grainAll'});
      add('feComposite', {in: 'grainAll', in2: 'shape', operator: 'in', result: 'grain'});
      const merge = add('feMerge', {});
      for (const n of ['paint', 'grain', 'rimIn']) merge.append(el('feMergeNode', {in: n}));
      const defs = el('defs', {}); defs.append(f); svg.append(defs);
      svg.append(el('path', {d: smooth(body), fill: v('--wash'), opacity: o.toFixed(3), filter: `url(#${id})`}));
    }
    host.append(svg);
  }
  return true;
}
"""
