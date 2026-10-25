// Rendu des blocs de vue (métriques, graphiques, tables, texte, Markdown, modèle).
// Partagé par le panneau des sorties et par les rapports HTML autonomes.

import { el, fmt } from "./ui.js";
import { renderChart } from "./charts.js";

export function staticTable(columns, rows) {
  const numeric = columns.map((_, j) => rows.some((r) => typeof r[j] === "number"));
  return el("div", { class: "mini-table" }, el("table", { class: "dtable" },
    el("thead", {}, el("tr", {}, el("th", { class: "idx" }, "#"), columns.map((c) => el("th", { style: { cursor: "default" } }, c)))),
    el("tbody", {}, rows.map((r, i) => el("tr", {}, el("td", { class: "idx" }, i),
      r.map((v, j) => v === null ? el("td", { class: "na" }, "NaN")
        : el("td", { class: numeric[j] ? "num" : "" }, numeric[j] ? fmt(v, 6) : String(v))))))));
}

// Markdown minimal et sûr : titres, gras, italique, code, liens, listes, citations.
export function renderMarkdown(text) {
  const box = el("div", { class: "markdown" });
  const inline = (s) => {
    const esc = s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    return esc
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>")
      .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  };
  let list = null, para = [];
  const flush = () => {
    if (para.length) { box.append(el("p", { html: inline(para.join(" ")) })); para = []; }
  };
  for (const raw of text.split("\n")) {
    const line = raw.trimEnd();
    const h = line.match(/^(#{1,4})\s+(.*)$/);
    const li = line.match(/^\s*(?:[-*]|\d+[.)])\s+(.*)$/);
    if (!line.trim()) { flush(); list = null; continue; }
    if (h) { flush(); list = null; box.append(el(`h${Math.min(6, h[1].length + 2)}`, { html: inline(h[2]) })); continue; }
    if (li) {
      flush();
      if (!list) { list = el(/^\s*\d/.test(line) ? "ol" : "ul"); box.append(list); }
      list.append(el("li", { html: inline(li[1]) }));
      continue;
    }
    if (line.startsWith(">")) { flush(); list = null; box.append(el("blockquote", { html: inline(line.replace(/^>\s?/, "")) })); continue; }
    list = null;
    para.push(line.trim());
  }
  flush();
  return box;
}

const KIND_FR = { classifier: "Classifieur", regressor: "Régresseur", cluster: "Clustering", transformer: "Transformeur" };

export function modelCard(s) {
  const kv = (k, v) => [el("dt", {}, k), el("dd", {}, v)];
  const params = Object.entries(s.params || {});
  const attrs = Object.entries(s.attributes || {});
  return el("div", { class: "model-card" },
    el("dl", { class: "kv" },
      kv("Estimateur", s.name), kv("Type", KIND_FR[s.kind] || s.kind),
      s.target ? kv("Cible", s.target) : null,
      kv(s.kind === "transformer" ? "Colonnes transformées" : "Variables", `${s.features.length} : ${s.features.slice(0, 30).join(", ")}${s.features.length > 30 ? "…" : ""}`),
      s.classes ? kv("Classes", s.classes.join(", ")) : null,
      s.output_columns ? kv("Colonnes produites", `${s.output_columns.length} : ${s.output_columns.slice(0, 20).join(", ")}${s.output_columns.length > 20 ? "…" : ""}`) : null),
    el("details", { open: true }, el("summary", {}, `Hyperparamètres (${params.length})`),
      el("dl", { class: "kv" }, params.map(([k, v]) => kv(k, v)))),
    attrs.length ? el("details", {}, el("summary", {}, `Attributs appris (${attrs.length})`),
      el("dl", { class: "kv" }, attrs.map(([k, v]) => kv(k, v)))) : null,
    el("details", {}, el("summary", {}, "Représentation Python"), el("div", { class: "vblock" }, el("pre", {}, s.repr))));
}

export function renderBlocks(blocks, container) {
  // Les graphiques consécutifs sont placés côte à côte.
  let row = null;
  for (const b of blocks) {
    if (b.type === "chart" && !["minihist", "heatmap", "tree"].includes(b.chart)) {
      if (!row) { row = el("div", { class: "charts-row" }); container.append(row); }
      const box = el("div", { class: "vblock" }, b.title ? el("h5", {}, b.title) : null);
      row.append(box);
      renderChart(b, box);
      continue;
    }
    row = null;
    if (b.type === "metrics") {
      container.append(el("div", { class: "metrics" }, b.items.map((m) => el("div", { class: "metric" },
        el("div", { class: "ml" }, m.label), el("div", { class: "mv" }, typeof m.value === "number" ? fmt(m.value, 4) : m.value)))));
    } else if (b.type === "table") {
      container.append(el("div", { class: "vblock" }, b.title ? el("h5", {}, b.title) : null,
        staticTable(b.columns, b.rows)));
    } else if (b.type === "text") {
      container.append(el("div", { class: "vblock" }, b.title ? el("h5", {}, b.title) : null, b.mono ? el("pre", {}, b.text) : el("p", { style: { margin: 0 } }, b.text)));
    } else if (b.type === "markdown") {
      container.append(el("div", { class: "vblock md" }, b.title ? el("h5", {}, b.title) : null, renderMarkdown(b.text || "")));
    } else if (b.type === "model") {
      container.append(el("div", { class: "vblock" }, el("h5", {}, "Modèle"), modelCard(b.summary)));
    } else if (b.type === "chart") {
      const box = el("div", { class: "vblock" }, b.title ? el("h5", {}, b.title) : null);
      container.append(box);
      renderChart(b, box);
    }
  }
}
