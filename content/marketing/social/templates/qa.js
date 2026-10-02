// Layout check run on every render (scripts/social_kit.py): text boxes marked [data-qa] must stay on the
// canvas and inside the design's safe zone, never be wider than their column, never overlap each other;
// every headline .line must stay on one line; [data-qa-orphans] paragraphs must not end with a lone word.
(safe) => {
  const issues = [];
  const W = window.innerWidth, H = window.innerHeight;
  const lineTops = (el) => {
    const r = document.createRange(); r.selectNodeContents(el);
    const tops = [];
    for (const rect of r.getClientRects()) {
      if (rect.width < 2) continue;
      if (!tops.some(t => Math.abs(t - rect.top) < rect.height * 0.5)) tops.push(rect.top);
    }
    return tops.length;
  };
  document.querySelectorAll('[data-qa]').forEach(el => {
    const name = el.dataset.qa;
    const b = el.getBoundingClientRect();
    if (b.width === 0) return;
    if (b.left < -0.5 || b.top < -0.5 || b.right > W + 0.5 || b.bottom > H + 0.5) issues.push(name + ': outside the canvas');
    if (safe && el.dataset.qaSafe !== 'off') {
      const [l, t, r, btm] = safe;
      if (b.left < l - 0.5 || b.top < t - 0.5 || b.right > r + 0.5 || b.bottom > btm + 0.5)
        issues.push(name + ': outside the safe zone ' + JSON.stringify([Math.round(b.left), Math.round(b.top), Math.round(b.right), Math.round(b.bottom)]));
    }
    if (el.scrollWidth > el.clientWidth + 2) issues.push(name + ': text is wider than its box');
    const parent = el.parentElement.getBoundingClientRect();
    if (el.dataset.qaSafe !== 'off' && (b.left < parent.left - 1 || b.right > parent.right + 1)) issues.push(name + ': wider than its column');
    el.querySelectorAll('.line').forEach((ln, i) => {
      const n = lineTops(ln);
      if (n > 1) issues.push(name + ': headline line ' + (i + 1) + ' wraps onto ' + n + ' lines');
    });
    if (el.dataset.qaOrphans !== undefined) {
      // the last rendered line of a paragraph must hold more than one word
      const r = document.createRange(); r.selectNodeContents(el);
      const rects = [...r.getClientRects()].filter(x => x.width > 2);
      if (rects.length) {
        const lastTop = Math.max(...rects.map(x => x.top));
        const tops = new Set(rects.map(x => Math.round(x.top)));
        if (tops.size > 1) {
          // measure words on the last line
          const text = el.textContent.trim().split(/\s+/);
          let count = 0;
          const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
          let node; const wr = document.createRange();
          while ((node = walker.nextNode())) {
            const re = /\S+/g; let m;
            while ((m = re.exec(node.data))) {
              wr.setStart(node, m.index); wr.setEnd(node, m.index + m[0].length);
              const rr = wr.getClientRects()[0];
              if (rr && Math.abs(rr.top - lastTop) < rr.height * 0.5) count++;
            }
          }
          if (count < 2) issues.push(name + ': single word on the last line');
        }
      }
    }
  });
  // text boxes must not overlap each other
  const boxes = [...document.querySelectorAll('[data-qa]')].map(el => [el.dataset.qa, el.getBoundingClientRect()]);
  for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
    const [na, a] = boxes[i], [nb, b] = boxes[j];
    if (a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1
        && !(a.top >= b.top && a.bottom <= b.bottom && a.left >= b.left && a.right <= b.right)
        && !(b.top >= a.top && b.bottom <= a.bottom && b.left >= a.left && b.right <= a.right))
      issues.push(na + ' overlaps ' + nb);
  }
  return issues;
}
