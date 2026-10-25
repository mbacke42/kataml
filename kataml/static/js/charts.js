// Mini-bibliothèque de graphiques SVG (sans dépendance), lisible en clair et sombre.
// Chaque fonction reçoit un bloc de vue renvoyé par le serveur et un conteneur.

import { el, svg, fmt } from "./ui.js";

const SERIES = ["--s1", "--s2", "--s3", "--s4", "--s5", "--s6", "--s7", "--s8"];
export const seriesColor = (i) => `var(${SERIES[i % SERIES.length]})`;

// ---------- Échelles & axes ----------
function niceTicks(min, max, count = 5) {
  if (!Number.isFinite(min) || !Number.isFinite(max)) return [0, 1];
  if (min === max) { min -= 1; max += 1; }
  const span = max - min;
  const step0 = span / count;
  const mag = 10 ** Math.floor(Math.log10(step0));
  const err = step0 / mag;
  const step = (err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1) * mag;
  const ticks = [];
  for (let v = Math.ceil(min / step) * step; v <= max + step * 1e-9; v += step) ticks.push(+v.toFixed(12));
  return ticks;
}

function logTicks([lo, hi]) {
  const out = [];
  for (let k = Math.ceil(lo - 1e-9); k <= Math.floor(hi + 1e-9); k++) out.push(k);
  return out.length >= 2 ? out : niceTicks(lo, hi);
}

function linear(d0, d1, r0, r1) {
  const k = d1 === d0 ? 0 : (r1 - r0) / (d1 - d0);
  const f = (v) => r0 + (v - d0) * k;
  f.domain = [d0, d1];
  return f;
}

function extent(arr) {
  let lo = Infinity, hi = -Infinity;
  for (const v of arr) if (v !== null && Number.isFinite(v)) { if (v < lo) lo = v; if (v > hi) hi = v; }
  return lo === Infinity ? [0, 1] : [lo, hi];
}

function padExtent([lo, hi], ratio = 0.04) {
  const p = (hi - lo || Math.abs(hi) || 1) * ratio;
  return [lo - p, hi + p];
}

const tickLabel = (v) => {
  const a = Math.abs(v);
  if (a >= 1e5 || (a > 0 && a < 1e-3)) return v.toExponential(1);
  return +v.toFixed(6) + "";
};

function frame(container, { height = 280, margin = {} } = {}) {
  const width = Math.max(260, container.clientWidth || 480);
  const m = { top: 12, right: 16, bottom: 42, left: 54, ...margin };
  const root = svg("svg", { width, height, viewBox: `0 0 ${width} ${height}`, role: "img" });
  return { root, width, height, m, iw: width - m.left - m.right, ih: height - m.top - m.bottom };
}

function axes(f, x, y, { xticks, yticks, xlabel, ylabel, xfmt = tickLabel, yfmt = tickLabel, xcat = null } = {}) {
  const { root, m, iw, ih } = f;
  const g = svg("g", { transform: `translate(${m.left},${m.top})` });
  const grid = svg("g", { class: "grid" });
  for (const t of yticks || []) grid.append(svg("line", { x1: 0, x2: iw, y1: y(t), y2: y(t) }));
  g.append(grid);
  const ax = svg("g", { class: "axis" });
  ax.append(svg("line", { x1: 0, x2: iw, y1: ih, y2: ih }));
  for (const t of yticks || []) {
    ax.append(svg("g", { class: "tick" }, svg("text", { x: -8, y: y(t) + 3.5, "text-anchor": "end" }, yfmt(t))));
  }
  if (xcat) {
    const step = Math.max(1, Math.ceil(xcat.length / Math.max(1, Math.floor(iw / 44))));
    xcat.forEach((lab, i) => {
      if (i % step) return;
      const cx = x(i);
      const s = String(lab);
      const t = svg("text", { x: cx, y: ih + 15, "text-anchor": xcat.length > 8 ? "end" : "middle",
        transform: xcat.length > 8 ? `rotate(-35 ${cx} ${ih + 15})` : null }, s.length > 16 ? s.slice(0, 15) + "…" : s);
      t.append(svg("title", {}, s));
      ax.append(svg("g", { class: "tick" }, t));
    });
  } else {
    for (const t of xticks || []) {
      ax.append(svg("line", { x1: x(t), x2: x(t), y1: ih, y2: ih + 4 }));
      ax.append(svg("g", { class: "tick" }, svg("text", { x: x(t), y: ih + 16, "text-anchor": "middle" }, xfmt(t))));
    }
  }
  g.append(ax);
  if (xlabel) root.append(svg("text", { class: "label", x: m.left + iw / 2, y: f.height - 4, "text-anchor": "middle" }, xlabel));
  if (ylabel) root.append(svg("text", { class: "label", x: -(m.top + ih / 2), y: 13, transform: "rotate(-90)", "text-anchor": "middle" }, ylabel));
  root.append(g);
  return g;
}

// ---------- Infobulle ----------
let tipEl = null;
function tip(evt, html) {
  if (!tipEl) { tipEl = el("div", { class: "chart-tip hidden" }); document.body.append(tipEl); }
  if (html === null) { tipEl.classList.add("hidden"); return; }
  tipEl.innerHTML = html;
  tipEl.classList.remove("hidden");
  const r = tipEl.getBoundingClientRect();
  tipEl.style.left = `${Math.min(evt.clientX + 14, innerWidth - r.width - 8)}px`;
  tipEl.style.top = `${Math.min(evt.clientY + 14, innerHeight - r.height - 8)}px`;
}
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
function hover(node, html) {
  node.addEventListener("mousemove", (e) => tip(e, typeof html === "function" ? html() : html));
  node.addEventListener("mouseleave", (e) => tip(e, null));
  return node;
}

function addLegend(box, names) {
  const lg = legend(names);
  if (lg) box.append(lg);
}

function legend(names, colorFn = seriesColor) {
  if (names.length < 2) return null;
  return el("div", { class: "legend" }, names.map((n, i) => el("span", {}, el("i", { style: { background: colorFn(i) } }), n)));
}

// ---------- Graphiques ----------
function scatter(b, box) {
  const n = b.x.length;
  let groups = null, gnames = [];
  if (b.groups) {
    gnames = [...new Set(b.groups)].slice(0, 8);
    groups = b.groups.map((g) => gnames.indexOf(g));
    if (new Set(b.groups).size > 8) groups = groups.map((g) => (g < 0 ? 7 : g));
  }
  if (gnames.length > 1) addLegend(box, gnames);
  const f = frame(box, { height: b.height || 320 });
  const xe = padExtent(extent(b.x)), ye = padExtent(extent(b.y));
  if (b.diagonal) { const lo = Math.min(xe[0], ye[0]), hi = Math.max(xe[1], ye[1]); xe[0] = ye[0] = lo; xe[1] = ye[1] = hi; }
  const x = linear(xe[0], xe[1], 0, f.iw), y = linear(ye[0], ye[1], f.ih, 0);
  const g = axes(f, x, y, { xticks: niceTicks(...xe), yticks: niceTicks(...ye), xlabel: b.xlabel, ylabel: b.ylabel });
  if (b.diagonal) g.append(svg("line", { x1: x(xe[0]), y1: y(xe[0]), x2: x(xe[1]), y2: y(xe[1]), stroke: "var(--muted)", "stroke-dasharray": "4 4" }));
  let cscale = null;
  if (b.cvalues) {
    const ce = extent(b.cvalues);
    cscale = (v) => `color-mix(in oklab, var(--s1) ${Math.round(100 * (v - ce[0]) / (ce[1] - ce[0] || 1))}%, var(--s4))`;
  }
  const r = n > 2000 ? 2.2 : n > 500 ? 3 : 4;
  const pts = svg("g", { "fill-opacity": n > 1500 ? 0.55 : 0.8 });
  for (let i = 0; i < n; i++) {
    if (b.x[i] === null || b.y[i] === null) continue;
    const fill = groups ? seriesColor(Math.max(groups[i], 0)) : cscale ? cscale(b.cvalues[i]) : seriesColor(0);
    pts.append(svg("circle", { cx: x(b.x[i]).toFixed(1), cy: y(b.y[i]).toFixed(1), r, fill, stroke: "var(--panel)", "stroke-width": n > 1500 ? 0 : 0.8, "data-i": i }));
  }
  pts.addEventListener("mousemove", (e) => {
    const i = e.target.dataset?.i;
    if (i === undefined) return tip(e, null);
    let h = `<b>${esc(b.xlabel || "x")}</b> ${fmt(b.x[i])}<br><b>${esc(b.ylabel || "y")}</b> ${fmt(b.y[i])}`;
    if (b.groups) h += `<br><b>${esc(b.clabel || "")}</b> ${esc(b.groups[i])}`;
    if (b.cvalues) h += `<br><b>${esc(b.clabel || "")}</b> ${fmt(b.cvalues[i])}`;
    tip(e, h);
  });
  pts.addEventListener("mouseleave", (e) => tip(e, null));
  g.append(pts);
  box.append(f.root);
}

function histogram(b, box) {
  const names = b.series.map((s) => s.name);
  if (names.length > 1) addLegend(box, names);
  const f = frame(box, { height: b.height || 260 });
  const e = b.edges;
  const ymax = Math.max(1, ...b.series.flatMap((s) => s.counts));
  const x = linear(e[0], e[e.length - 1], 0, f.iw), y = linear(0, ymax * 1.05, f.ih, 0);
  const g = axes(f, x, y, { xticks: niceTicks(e[0], e[e.length - 1], 6), yticks: niceTicks(0, ymax), xlabel: b.xlabel, ylabel: b.ylabel });
  const multi = b.series.length > 1;
  b.series.forEach((s, si) => {
    const grp = svg("g", { "fill-opacity": multi ? 0.5 : 0.9 });
    s.counts.forEach((c, i) => {
      if (!c) return;
      const x0 = x(e[i]) + 1, x1 = x(e[i + 1]) - 1;
      const rect = svg("rect", { class: "mark", x: x0, y: y(c), width: Math.max(1, x1 - x0), height: f.ih - y(c), fill: seriesColor(si), rx: 2 });
      hover(rect, `${multi ? `<b>${esc(s.name)}</b><br>` : ""}[${fmt(e[i], 3)} ; ${fmt(e[i + 1], 3)}[<br>Effectif : <b>${fmt(c)}</b>`);
      grp.append(rect);
    });
    g.append(grp);
  });
  box.append(f.root);
}

function bar(b, box, horizontal = false) {
  const labels = b.labels, values = b.values;
  if (horizontal) {
    const rowH = 22;
    const longest = Math.min(26, Math.max(...labels.map((l) => String(l).length)));
    const f = frame(box, { height: labels.length * rowH + 50, margin: { left: Math.max(60, longest * 6.6 + 12), bottom: 32 } });
    const lo = Math.min(0, ...values.map((v, i) => v - (b.errors?.[i] || 0)));
    const hi = Math.max(0, ...values.map((v, i) => v + (b.errors?.[i] || 0)));
    const x = linear(lo, hi * 1.04 || 1, 0, f.iw);
    const g = svg("g", { transform: `translate(${f.m.left},${f.m.top})` });
    const ticks = niceTicks(lo, hi || 1);
    const grid = svg("g", { class: "grid" });
    ticks.forEach((t) => grid.append(svg("line", { x1: x(t), x2: x(t), y1: 0, y2: labels.length * rowH })));
    g.append(grid);
    ticks.forEach((t) => g.append(svg("g", { class: "tick" }, svg("text", { x: x(t), y: labels.length * rowH + 16, "text-anchor": "middle" }, tickLabel(t)))));
    labels.forEach((lab, i) => {
      const v = values[i], yy = i * rowH + 3, h = rowH - 7;
      const s = String(lab);
      g.append(svg("g", { class: "tick" }, svg("text", { x: -8, y: yy + h / 2 + 4, "text-anchor": "end" }, s.length > 26 ? s.slice(0, 25) + "…" : s)));
      const x0 = Math.min(x(0), x(v)), w = Math.abs(x(v) - x(0));
      const rect = svg("rect", { class: "mark", x: x0, y: yy, width: Math.max(1, w), height: h, rx: 3, fill: v < 0 ? seriesColor(1) : seriesColor(0) });
      hover(rect, `<b>${esc(s)}</b><br>${fmt(v)}${b.errors ? ` ± ${fmt(b.errors[i])}` : ""}`);
      g.append(rect);
      if (b.errors?.[i]) g.append(svg("line", { x1: x(v - b.errors[i]), x2: x(v + b.errors[i]), y1: yy + h / 2, y2: yy + h / 2, stroke: "var(--text-2)", "stroke-width": 1.2 }));
    });
    g.append(svg("line", { x1: x(0), x2: x(0), y1: 0, y2: labels.length * rowH, stroke: "var(--axis)" }));
    f.root.append(g);
    box.append(f.root);
    return;
  }
  const f = frame(box, { height: b.height || 260, margin: { bottom: labels.length > 8 ? 70 : 42 } });
  const ymax = Math.max(...values, ...(b.cumulative || []), 0) || 1;
  const bw = f.iw / labels.length;
  const x = (i) => i * bw + bw / 2;
  const y = linear(0, ymax * 1.06, f.ih, 0);
  const g = axes(f, x, y, { yticks: niceTicks(0, ymax), xcat: labels, xlabel: labels.length > 8 ? null : b.xlabel, ylabel: b.ylabel });
  labels.forEach((lab, i) => {
    const w = Math.max(2, Math.min(bw - 4, 64));
    const rect = svg("rect", { class: "mark", x: x(i) - w / 2, y: y(values[i]), width: w, height: f.ih - y(values[i]), rx: 3, fill: seriesColor(0) });
    hover(rect, `<b>${esc(lab)}</b><br>${fmt(values[i])}${b.cumulative ? `<br>Cumul : ${fmt(b.cumulative[i])}` : ""}`);
    g.append(rect);
  });
  if (b.cumulative) {
    const d = b.cumulative.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join("");
    g.append(svg("path", { d, fill: "none", stroke: seriesColor(1), "stroke-width": 2 }));
    b.cumulative.forEach((v, i) => g.append(svg("circle", { cx: x(i), cy: y(v), r: 3, fill: seriesColor(1) })));
    box.prepend(el("div", { class: "legend" }, el("span", {}, el("i", { style: { background: seriesColor(0) } }), "Par composante"),
      el("span", {}, el("i", { style: { background: seriesColor(1) } }), "Cumulée")));
  }
  box.append(f.root);
}

function groupedbar(b, box) {
  addLegend(box, b.series.map((s) => s.name));
  const f = frame(box, { height: b.height || 260 });
  const all = b.series.flatMap((s) => s.values);
  const lo = Math.min(0, ...all), hi = Math.max(0, ...all) || 1;
  const bw = f.iw / b.labels.length;
  const x = (i) => i * bw + bw / 2;
  const y = linear(lo, hi * 1.06, f.ih, 0);
  const g = axes(f, x, y, { yticks: niceTicks(lo, hi), xcat: b.labels });
  const k = b.series.length;
  const w = Math.min(28, (bw - 10) / k);
  b.labels.forEach((lab, i) => {
    b.series.forEach((s, si) => {
      const v = s.values[i];
      const x0 = x(i) - (k * w) / 2 + si * w;
      const rect = svg("rect", { class: "mark", x: x0 + 1, y: Math.min(y(v), y(0)), width: Math.max(1, w - 2), height: Math.abs(y(v) - y(0)), rx: 2, fill: seriesColor(si) });
      hover(rect, `<b>${esc(lab)}</b><br>${esc(s.name)} : ${fmt(v)}`);
      g.append(rect);
    });
  });
  box.append(f.root);
}

function heatmap(b, box) {
  const n = b.labels.length, m = b.ylabels.length;
  const flat = b.matrix.flat().filter((v) => v !== null);
  const vmin = b.vmin ?? Math.min(...flat), vmax = b.vmax ?? Math.max(...flat);
  const maxLab = Math.min(22, Math.max(...b.ylabels.map((l) => String(l).length)));
  const cell = Math.max(14, Math.min(56, Math.floor(((box.clientWidth || 480) - maxLab * 6.5 - 40) / n)));
  const f = frame(box, { height: m * cell + 90, margin: { left: maxLab * 6.5 + 24, bottom: 78, top: 8 } });
  const g = svg("g", { transform: `translate(${f.m.left},${f.m.top})` });
  const color = (v) => {
    if (v === null) return "var(--panel-2)";
    if (b.diverging) {
      const t = Math.max(-1, Math.min(1, v / (Math.max(Math.abs(vmin), Math.abs(vmax)) || 1)));
      return t >= 0 ? `color-mix(in oklab, var(--s1) ${Math.round(t * 100)}%, var(--panel-2))`
                    : `color-mix(in oklab, var(--s8) ${Math.round(-t * 100)}%, var(--panel-2))`;
    }
    const t = (v - vmin) / (vmax - vmin || 1);
    return `color-mix(in oklab, var(--s1) ${Math.round(8 + t * 92)}%, var(--panel-2))`;
  };
  const annot = b.annot || cell >= 34;
  b.matrix.forEach((row, i) => row.forEach((v, j) => {
    const r = svg("rect", { class: "mark", x: j * cell + 1, y: i * cell + 1, width: cell - 2, height: cell - 2, rx: 3, fill: color(v) });
    hover(r, `<b>${esc(b.ylabels[i])}</b> × <b>${esc(b.labels[j])}</b><br>${fmt(v)}`);
    g.append(r);
    if (annot && v !== null) {
      const t = b.diverging ? Math.abs(v) / (Math.max(Math.abs(vmin), Math.abs(vmax)) || 1) : (v - vmin) / (vmax - vmin || 1);
      g.append(svg("text", { x: j * cell + cell / 2, y: i * cell + cell / 2 + 4, "text-anchor": "middle", "pointer-events": "none",
        style: `fill:${t > 0.55 ? "#fff" : "var(--text)"};font-size:${cell < 40 ? 10 : 12}px;font-weight:560` }, fmt(v, cell < 40 ? 2 : 3)));
    }
  }));
  b.ylabels.forEach((l, i) => { const s = String(l); g.append(svg("g", { class: "tick" }, svg("text", { x: -8, y: i * cell + cell / 2 + 4, "text-anchor": "end" }, s.length > 22 ? s.slice(0, 21) + "…" : s))); });
  b.labels.forEach((l, j) => {
    const s = String(l), cx = j * cell + cell / 2, cy = m * cell + 12;
    g.append(svg("g", { class: "tick" }, svg("text", { x: cx, y: cy, "text-anchor": "end", transform: `rotate(-40 ${cx} ${cy})` }, s.length > 18 ? s.slice(0, 17) + "…" : s)));
  });
  if (b.xlabel) f.root.append(svg("text", { class: "label", x: f.m.left + (n * cell) / 2, y: f.height - 4, "text-anchor": "middle" }, b.xlabel));
  if (b.ylabel) f.root.append(svg("text", { class: "label", x: -(f.m.top + (m * cell) / 2), y: 12, transform: "rotate(-90)", "text-anchor": "middle" }, b.ylabel));
  f.root.setAttribute("width", Math.min(f.width, f.m.left + n * cell + 20));
  f.root.setAttribute("viewBox", `0 0 ${Math.min(f.width, f.m.left + n * cell + 20)} ${f.height}`);
  f.root.append(g);
  box.append(f.root);
}

function line(b, box) {
  addLegend(box, b.series.map((s) => s.name));
  const f = frame(box, { height: b.height || 300 });
  if (b.xlog) b = { ...b, series: b.series.map((s) => ({ ...s, x: s.x.map((v) => Math.log10(v)) })), xlogged: true };
  const xs = b.series.flatMap((s) => s.x);
  const ys = b.series.flatMap((s) => s.y.map((v, i) => [v - (s.band?.[i] || 0), v + (s.band?.[i] || 0)]).flat());
  const xe = b.domain ? b.domain : extent(xs);
  const ye = b.domain ? [0, 1.02] : padExtent(extent(ys), 0.08);
  const x = linear(xe[0], xe[1], 0, f.iw), y = linear(ye[0], ye[1], f.ih, 0);
  const xticks = b.xlogged ? logTicks(xe) : niceTicks(...xe);
  const xfmt = b.xlogged ? (v) => fmt(10 ** v, 4) : tickLabel;
  const g = axes(f, x, y, { xticks, yticks: niceTicks(...ye), xlabel: b.xlabel, ylabel: b.ylabel, xfmt });
  if (b.diagonal) g.append(svg("line", { x1: x(0), y1: y(0), x2: x(1), y2: y(1), stroke: "var(--muted)", "stroke-dasharray": "4 4" }));
  b.series.forEach((s, si) => {
    const c = seriesColor(si);
    if (s.band) {
      const up = s.x.map((xv, i) => `${i ? "L" : "M"}${x(xv)},${y(s.y[i] + s.band[i])}`).join("");
      const dn = s.x.map((xv, i) => `L${x(xv)},${y(s.y[i] - s.band[i])}`).reverse().join("");
      g.append(svg("path", { d: up + dn + "Z", fill: c, "fill-opacity": 0.14, stroke: "none" }));
    }
    const d = s.x.map((xv, i) => `${i ? "L" : "M"}${x(xv).toFixed(1)},${y(s.y[i]).toFixed(1)}`).join("");
    g.append(svg("path", { d, fill: "none", stroke: c, "stroke-width": 2, "stroke-linejoin": "round" }));
    if (b.markers) s.x.forEach((xv, i) => g.append(hover(svg("circle", { cx: x(xv), cy: y(s.y[i]), r: 4, fill: c, stroke: "var(--panel)", "stroke-width": 2 }),
      `<b>${esc(s.name)}</b><br>${esc(b.xlabel || "x")} : ${fmt(b.xlogged ? 10 ** xv : xv)}<br>${esc(b.ylabel || "y")} : ${fmt(s.y[i])}`)));
  });
  // Réticule
  const cross = svg("line", { y1: 0, y2: f.ih, stroke: "var(--muted)", "stroke-dasharray": "3 3", visibility: "hidden" });
  g.append(cross);
  const hit = svg("rect", { x: 0, y: 0, width: f.iw, height: f.ih, fill: "transparent" });
  hit.addEventListener("mousemove", (e) => {
    const r = hit.getBoundingClientRect();
    const xv = xe[0] + ((e.clientX - r.left) / r.width) * (xe[1] - xe[0]);
    cross.setAttribute("x1", x(xv)); cross.setAttribute("x2", x(xv)); cross.setAttribute("visibility", "visible");
    const rows = b.series.map((s, si) => {
      let best = 0;
      s.x.forEach((v, i) => { if (Math.abs(v - xv) < Math.abs(s.x[best] - xv)) best = i; });
      return `<span style="color:${seriesColor(si)}">●</span> ${esc(s.name)} : <b>${fmt(s.y[best], 3)}</b>`;
    });
    tip(e, `${esc(b.xlabel || "x")} ≈ ${fmt(b.xlogged ? 10 ** xv : xv, 3)}<br>${rows.join("<br>")}`);
  });
  hit.addEventListener("mouseleave", (e) => { cross.setAttribute("visibility", "hidden"); tip(e, null); });
  g.prepend(hit);
  box.append(f.root);
}

function box(b, container) {
  const boxes = b.boxes;
  const f = frame(container, { height: b.height || 300, margin: { bottom: boxes.length > 6 ? 80 : 42 } });
  const all = boxes.flatMap((d) => [d.lo, d.hi, ...d.outliers]);
  const ye = padExtent(extent(all), 0.06);
  const bw = f.iw / boxes.length;
  const x = (i) => i * bw + bw / 2;
  const y = linear(ye[0], ye[1], f.ih, 0);
  const g = axes(f, x, y, { yticks: niceTicks(...ye), xcat: boxes.map((d) => d.label) });
  boxes.forEach((d, i) => {
    const c = seriesColor(0), w = Math.min(40, bw * 0.55), cx = x(i);
    const grp = svg("g", { class: "mark" });
    grp.append(svg("line", { x1: cx, x2: cx, y1: y(d.lo), y2: y(d.q1), stroke: "var(--text-2)" }));
    grp.append(svg("line", { x1: cx, x2: cx, y1: y(d.q3), y2: y(d.hi), stroke: "var(--text-2)" }));
    grp.append(svg("line", { x1: cx - w / 4, x2: cx + w / 4, y1: y(d.lo), y2: y(d.lo), stroke: "var(--text-2)" }));
    grp.append(svg("line", { x1: cx - w / 4, x2: cx + w / 4, y1: y(d.hi), y2: y(d.hi), stroke: "var(--text-2)" }));
    grp.append(svg("rect", { x: cx - w / 2, y: y(d.q3), width: w, height: Math.max(1, y(d.q1) - y(d.q3)), rx: 3, fill: c, "fill-opacity": 0.25, stroke: c, "stroke-width": 1.5 }));
    grp.append(svg("line", { x1: cx - w / 2, x2: cx + w / 2, y1: y(d.median), y2: y(d.median), stroke: c, "stroke-width": 2.5 }));
    d.outliers.forEach((o) => grp.append(svg("circle", { cx, cy: y(o), r: 2.5, fill: "none", stroke: "var(--text-2)" })));
    hover(grp, `<b>${esc(d.label)}</b><br>Max (moustache) : ${fmt(d.hi)}<br>Q3 : ${fmt(d.q3)}<br>Médiane : ${fmt(d.median)}<br>Q1 : ${fmt(d.q1)}<br>Min (moustache) : ${fmt(d.lo)}<br>Valeurs extrêmes : ${d.outliers.length}`);
    g.append(grp);
  });
  container.append(f.root);
}

function minihist(b, container) {
  const grid = el("div", { class: "minihists" });
  for (const it of b.items) {
    const card = el("div", { class: "minihist" }, el("div", { class: "t", title: it.title }, it.title));
    const W = 170, H = 54;
    const s = svg("svg", { width: "100%", height: H, viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "none" });
    const vals = it.counts || it.values;
    const mx = Math.max(1, ...vals);
    const bw = W / vals.length;
    vals.forEach((v, i) => {
      const h = (v / mx) * (H - 4);
      const r = svg("rect", { class: "mark", x: i * bw + 0.5, y: H - h, width: Math.max(1, bw - 1.5), height: h, rx: 1.5, fill: it.counts ? seriesColor(0) : seriesColor(1) });
      hover(r, it.counts ? `[${fmt(it.edges[i], 3)} ; ${fmt(it.edges[i + 1], 3)}[ : <b>${fmt(v)}</b>` : `${esc(it.labels[i])} : <b>${fmt(v)}</b>`);
      s.append(r);
    });
    card.append(s);
    if (it.counts) card.append(el("div", { class: "legend", style: { justifyContent: "space-between", margin: 0, fontSize: "10.5px" } },
      el("span", {}, fmt(it.edges[0], 3)), el("span", {}, fmt(it.edges[it.edges.length - 1], 3))));
    else card.append(el("div", { class: "legend", style: { margin: 0, fontSize: "10.5px" } }, `${it.labels.length} modalité(s) principales`));
    grid.append(card);
  }
  container.append(grid);
}

// Couleur réelle d'une variable CSS (pour le dessin sur canvas).
function cssColor(name) {
  const probe = document.createElement("span");
  probe.style.color = name.startsWith("var(") ? name : `var(${name})`;
  document.body.append(probe);
  const rgb = getComputedStyle(probe).color.match(/[\d.]+/g).slice(0, 3).map(Number);
  probe.remove();
  return rgb;
}

function decision(b, box) {
  const continuous = !!b.continuous;
  if (!continuous && b.classes.length > 1) addLegend(box, b.classes);
  const f = frame(box, { height: b.height || 380 });
  const x = linear(b.x0, b.x1, 0, f.iw), y = linear(b.y0, b.y1, f.ih, 0);
  const g = axes(f, x, y, { xticks: niceTicks(b.x0, b.x1), yticks: niceTicks(b.y0, b.y1), xlabel: b.xlabel, ylabel: b.ylabel });
  const canvas = document.createElement("canvas");
  canvas.width = b.nx; canvas.height = b.ny;
  const c2d = canvas.getContext("2d");
  const img = c2d.createImageData(b.nx, b.ny);
  const surface = cssColor("--panel");
  const palette = SERIES.map((v) => cssColor(v));
  const lo = continuous ? Math.min(...b.z) : 0, hi = continuous ? Math.max(...b.z) : 1;
  const ramp = (t) => palette[0].map((c, k) => c * t + palette[3][k] * (1 - t));
  for (let j = 0; j < b.ny; j++) {
    for (let i = 0; i < b.nx; i++) {
      const v = b.z[j * b.nx + i];
      let rgb, a;
      if (continuous) { rgb = ramp((v - lo) / (hi - lo || 1)); a = 0.55; }
      else { rgb = v < 0 ? surface : palette[v % palette.length]; a = 0.18 + 0.42 * (b.conf ? (b.conf[j * b.nx + i] - 1 / b.classes.length) / (1 - 1 / b.classes.length || 1) : 0.6); }
      const o = ((b.ny - 1 - j) * b.nx + i) * 4;
      for (let k = 0; k < 3; k++) img.data[o + k] = Math.round(rgb[k] * a + surface[k] * (1 - a));
      img.data[o + 3] = 255;
    }
  }
  c2d.putImageData(img, 0, 0);
  g.prepend(svg("image", { href: canvas.toDataURL(), x: 0, y: 0, width: f.iw, height: f.ih, preserveAspectRatio: "none" }));
  const pts = svg("g", {});
  b.px.forEach((px, i) => {
    let fill;
    if (continuous) fill = b.pv ? `rgb(${ramp((b.pv[i] - lo) / (hi - lo || 1)).join(",")})` : "var(--text)";
    else fill = seriesColor(Math.max(0, b.pc[i]));
    pts.append(svg("circle", { cx: x(px).toFixed(1), cy: y(b.py[i]).toFixed(1), r: b.px.length > 800 ? 2.5 : 3.5, fill,
      stroke: "var(--panel)", "stroke-width": 1, "data-i": i }));
  });
  pts.addEventListener("mousemove", (e) => {
    const i = e.target.dataset?.i;
    if (i === undefined) return tip(e, null);
    const lab = continuous ? (b.pv ? `Valeur : <b>${fmt(b.pv[i])}</b>` : "") : `Classe : <b>${esc(b.classes[b.pc[i]] ?? "?")}</b>`;
    tip(e, `${esc(b.xlabel)} ${fmt(b.px[i])}<br>${esc(b.ylabel)} ${fmt(b.py[i])}<br>${lab}`);
  });
  pts.addEventListener("mouseleave", (e) => tip(e, null));
  g.append(pts);
  box.append(f.root);
  if (continuous) box.append(el("div", { class: "legend" }, `Prédiction : de ${fmt(lo, 3)} (orange) à ${fmt(hi, 3)} (bleu)`));
}

function tree(b, container) {
  const W = 168, H = 62, GX = 14, GY = 46;
  // Placement : chaque feuille visible occupe une colonne.
  let col = 0;
  const place = (n, depth) => {
    n.depth = depth;
    if (n.children) {
      n.children.forEach((c) => place(c, depth + 1));
      n.cx = (n.children[0].cx + n.children[1].cx) / 2;
    } else { n.cx = col * (W + GX) + W / 2; col++; }
    return n;
  };
  const root = place(structuredClone(b.root), 0);
  let maxDepth = 0;
  const walk = (n, fn) => { fn(n); (n.children || []).forEach((c) => walk(c, fn)); };
  walk(root, (n) => { maxDepth = Math.max(maxDepth, n.depth); });
  const width = col * (W + GX), height = (maxDepth + 1) * (H + GY) + 10;
  const s = svg("svg", { width, height, viewBox: `0 0 ${width} ${height}`, role: "img" });
  const classIndex = (name) => (b.classes || []).indexOf(name);
  const yOf = (n) => n.depth * (H + GY) + 4;
  walk(root, (n) => {
    (n.children || []).forEach((c, k) => {
      const x1 = n.cx, y1 = yOf(n) + H, x2 = c.cx, y2 = yOf(c);
      s.append(svg("path", { d: `M${x1},${y1} C${x1},${y1 + GY / 2} ${x2},${y2 - GY / 2} ${x2},${y2}`, fill: "none", stroke: "var(--edge)", "stroke-width": 1.5 }));
      s.append(svg("text", { x: (x1 + x2) / 2 + (k ? 6 : -6), y: (y1 + y2) / 2, "text-anchor": k ? "start" : "end", style: "font-size:10.5px;fill:var(--muted)" }, k ? "non" : "oui"));
    });
  });
  walk(root, (n) => {
    const ci = n.class !== undefined ? classIndex(n.class) : -1;
    const purity = n.dist ? Math.max(...n.dist) : 0.5;
    const fill = ci >= 0 ? `color-mix(in oklab, ${seriesColor(ci)} ${Math.round(12 + 50 * purity * purity)}%, var(--panel))` : "var(--panel-2)";
    const gx = svg("g", { class: "mark" });
    gx.append(svg("rect", { x: n.cx - W / 2, y: yOf(n), width: W, height: H, rx: 8, fill, stroke: n.children || n.truncated ? "var(--line-strong)" : "var(--text-2)", "stroke-width": n.children ? 1 : 1.4 }));
    const lines = [n.rule || "Feuille", `n = ${n.samples} · ${b.criterion || "impureté"} = ${n.impurity}`,
      n.class !== undefined ? `classe : ${n.class}` : `valeur : ${fmt(n.value)}`];
    lines.forEach((t, k) => gx.append(svg("text", { x: n.cx, y: yOf(n) + 18 + k * 16, "text-anchor": "middle",
      style: `font-size:${k ? 11 : 11.5}px;font-weight:${k ? 400 : 620};fill:var(--text)` }, t.length > 26 ? t.slice(0, 25) + "…" : t)));
    if (n.truncated) gx.append(svg("text", { x: n.cx, y: yOf(n) + H + 14, "text-anchor": "middle", style: "fill:var(--muted)" }, "…"));
    const dist = n.dist ? b.classes.map((c, k) => `${esc(c)} : ${(n.dist[k] * 100).toFixed(1)} %`).join("<br>") : "";
    hover(gx, `<b>${esc(n.rule || "Feuille")}</b><br>Échantillons : ${n.samples}<br>Impureté : ${n.impurity}${dist ? "<br>" + dist : ""}${n.value !== undefined ? `<br>Valeur : ${fmt(n.value)}` : ""}`);
    s.append(gx);
  });
  container.append(el("div", { style: { overflowX: "auto", paddingBottom: "6px" } }, s));
}

const RENDERERS = {
  scatter, histogram, bar, groupedbar, heatmap, line, box, minihist, decision, tree,
  hbar: (b, c) => bar(b, c, true),
};

export function renderChart(block, container) {
  const wrap = el("div", { class: "chart" });
  container.append(wrap);
  const fn = RENDERERS[block.chart];
  if (!fn) { wrap.append(el("div", {}, `Graphique « ${block.chart} » non pris en charge.`)); return wrap; }
  const draw = () => { wrap.replaceChildren(); fn(block, wrap); };
  draw();
  // Redessine à la largeur du conteneur.
  let lastW = wrap.clientWidth;
  const ro = new ResizeObserver(() => {
    if (Math.abs(wrap.clientWidth - lastW) > 30) { lastW = wrap.clientWidth; draw(); }
  });
  ro.observe(wrap);
  return wrap;
}

// Petit histogramme pour les profils de colonnes.
export function sparkHist(counts, color = seriesColor(0)) {
  const W = 180, H = 36;
  const s = svg("svg", { width: "100%", height: H, viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "none" });
  const mx = Math.max(1, ...counts);
  const bw = W / counts.length;
  counts.forEach((v, i) => {
    const h = (v / mx) * (H - 2);
    s.append(svg("rect", { x: i * bw + 0.5, y: H - h, width: Math.max(1, bw - 1.5), height: h, rx: 1.5, fill: color }));
  });
  return s;
}
