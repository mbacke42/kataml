// Panneau inférieur : tables des ports de sortie, modèles et vues des nœuds.

import { el, icon, fmt, dtypeClass, toast } from "./ui.js";
import { api } from "./api.js";
import { store, spec, nodeById, on } from "./state.js";
import { sparkHist, seriesColor } from "./charts.js";
import { modelCard, renderBlocks } from "./blocks.js";

let tabsEl, bodyEl, actionsEl;
let current = { node: null, tab: null };   // tab : "view" | numéro de port
const tableState = { offset: 0, limit: 100, sort: null, desc: false, mode: "table" };
let reqSeq = 0;

export function initOutputs() {
  tabsEl = document.getElementById("out-tabs");
  bodyEl = document.getElementById("out-body");
  actionsEl = document.getElementById("out-actions");
  on("selection", () => {
    const ids = [...store.selection].filter((id) => nodeById(id));
    if (ids.length === 1 && ids[0] !== current.node) show(ids[0]);
    else if (!ids.length) show(null);
  });
  on("show-port", ({ node, port }) => show(node, port));
  on("states", () => { if (current.node) show(current.node, current.tab, true); });
  show(null);
}

function defaultTab(node, st) {
  const sp = spec(node.type);
  if (st?.has_view) return "view";
  const firstData = sp.outputs.findIndex((o) => o.kind === "data");
  return firstData >= 0 ? firstData : sp.outputs.length ? 0 : null;
}

export function show(id, tab = undefined, keep = false) {
  const node = id ? nodeById(id) : null;
  const st = node ? store.states[id] : null;
  if (!keep || current.node !== id) Object.assign(tableState, { offset: 0, sort: null, desc: false });
  if (!node) {
    current = { node: null, tab: null };
    tabsEl.replaceChildren(el("span", { class: "tab", style: { cursor: "default" } }, icon("i-table"), "Sorties"));
    actionsEl.replaceChildren();
    bodyEl.replaceChildren(el("div", { class: "bottom-empty" }, "Sélectionnez un nœud exécuté pour afficher ses tables, son modèle ou sa vue."));
    return;
  }
  const sp = spec(node.type);
  const executed = st?.state === "executed";
  if (tab === undefined || tab === null) tab = executed ? defaultTab(node, st) : null;
  if (tab === "view" && !st?.has_view) tab = defaultTab(node, st);
  const prevTab = current.tab, prevNode = current.node;
  current = { node: id, tab };
  // Onglets
  const tabs = [];
  if (sp.has_view) {
    tabs.push(el("button", { class: `tab${tab === "view" ? " on" : ""}`, disabled: !st?.has_view, onclick: () => show(id, "view", true) },
      icon("i-chart"), "Vue"));
  }
  sp.outputs.forEach((o, i) => {
    const info = st?.outputs?.[i];
    const meta = info?.kind === "data" ? `${fmt(info.rows)} × ${info.cols}` : info?.kind === "model" ? info.name : "";
    tabs.push(el("button", { class: `tab${tab === i ? " on" : ""}`, disabled: !executed, onclick: () => show(id, i, true) },
      el("span", { class: `pg ${o.kind}` }), o.name, meta ? el("span", { class: "meta" }, meta) : null));
  });
  if (!tabs.length) tabs.push(el("span", { class: "tab" }, sp.name));
  tabsEl.replaceChildren(...tabs);
  actionsEl.replaceChildren();
  if (!executed) {
    const label = node.label || sp.name;
    bodyEl.replaceChildren(el("div", { class: "bottom-empty" },
      st?.state === "error" ? el("div", {}, el("b", {}, "Erreur : "), st.message)
        : st?.state === "running" ? "Exécution en cours…"
        : el("div", {}, `« ${label} » n'est pas encore exécuté. `, el("button", { class: "btn sm primary", onclick: () => import("./state.js").then((m) => m.emit("execute", [id])) }, icon("i-play"), "Exécuter"))));
    return;
  }
  if (keep && prevNode === id && prevTab === tab && tab !== "view" && typeof tab === "number" && sp.outputs[tab]?.kind === "data") {
    loadTable(id, tab);
    return;
  }
  if (tab === "view") loadView(id);
  else if (tab !== null && sp.outputs[tab]?.kind === "data") loadTable(id, tab);
  else if (tab !== null) loadModel(id, tab);
  else bodyEl.replaceChildren(el("div", { class: "bottom-empty" }, "Ce nœud n'a pas de sortie."));
}

function downloadBtn(id, port, label, name) {
  return el("a", { class: "btn sm", href: api.downloadUrl(id, port, name), title: `Télécharger (${label})` }, icon("i-download"), label);
}

function baseName(id) {
  const n = nodeById(id);
  return (n?.label || spec(n?.type)?.name || "sortie").replace(/\s+/g, "_");
}

// ---------- Tables ----------
async function loadTable(id, port) {
  const seq = ++reqSeq;
  const modeSeg = el("div", { class: "seg" },
    el("button", { class: tableState.mode === "table" ? "on" : "", onclick: () => { tableState.mode = "table"; loadTable(id, port); } }, icon("i-table"), "Table"),
    el("button", { class: tableState.mode === "profile" ? "on" : "", onclick: () => { tableState.mode = "profile"; loadTable(id, port); } }, icon("i-chart"), "Profil"));
  actionsEl.replaceChildren(modeSeg, downloadBtn(id, port, "CSV", baseName(id)));
  try {
    if (tableState.mode === "profile") {
      const res = await api.profile(id, port);
      if (seq !== reqSeq) return;
      bodyEl.replaceChildren(profiles(res.columns));
      return;
    }
    const res = await api.port(id, port, { offset: tableState.offset, limit: tableState.limit, sort: tableState.sort, desc: tableState.desc });
    if (seq !== reqSeq) return;
    bodyEl.replaceChildren(dataTable(res, () => loadTable(id, port)));
  } catch (e) {
    if (seq !== reqSeq) return;
    bodyEl.replaceChildren(el("div", { class: "bottom-empty" }, e.message));
  }
}

export function dataTable(res, reload) {
  const cols = res.columns;
  const numeric = cols.map((c) => dtypeClass(c.dtype) === "num");
  const thead = el("tr", {}, el("th", { class: "idx" }, "#"), cols.map((c, j) => el("th", {
    title: `${c.name} (${c.dtype}) — cliquer pour trier`,
    onclick: reload ? () => {
      if (tableState.sort === c.name) { if (tableState.desc) { tableState.sort = null; tableState.desc = false; } else tableState.desc = true; }
      else { tableState.sort = c.name; tableState.desc = false; }
      tableState.offset = 0;
      reload();
    } : null,
  }, el("div", { class: "th" }, el("span", {}, c.name, tableState.sort === c.name ? el("span", { class: "sort" }, tableState.desc ? "↓" : "↑") : null),
    reload ? el("span", { class: "dt" }, c.dtype) : null))));
  const rows = res.rows.map((r, i) => el("tr", {}, el("td", { class: "idx" }, res.index ? res.index[i] : res.offset + i),
    r.map((v, j) => {
      if (v === null) return el("td", { class: "na" }, "NaN");
      return el("td", { class: numeric[j] ? "num" : "", title: String(v).length > 40 ? String(v) : null }, numeric[j] ? fmt(v, 6) : String(v));
    })));
  const table = el("table", { class: "dtable" }, el("thead", {}, thead), el("tbody", {}, rows));
  if (!reload) return el("div", { class: "mini-table" }, table);
  const { offset, limit } = tableState;
  const total = res.total;
  const pager = el("div", { class: "pager" },
    el("span", {}, `${fmt(total)} lignes · ${cols.length} colonnes`),
    el("span", { class: "sp" }),
    el("span", {}, total ? `${fmt(offset + 1)}–${fmt(Math.min(offset + limit, total))}` : "0"),
    el("button", { class: "btn sm icon", title: "Début", disabled: offset === 0, onclick: () => { tableState.offset = 0; reload(); } }, "«"),
    el("button", { class: "btn sm icon", title: "Précédent", disabled: offset === 0, onclick: () => { tableState.offset = Math.max(0, offset - limit); reload(); } }, "‹"),
    el("button", { class: "btn sm icon", title: "Suivant", disabled: offset + limit >= total, onclick: () => { tableState.offset = offset + limit; reload(); } }, "›"),
    el("button", { class: "btn sm icon", title: "Fin", disabled: offset + limit >= total, onclick: () => { tableState.offset = Math.max(0, Math.floor((total - 1) / limit) * limit); reload(); } }, "»"));
  return el("div", { class: "dtable-wrap" }, el("div", { class: "dtable-scroll" }, table), pager);
}

function profiles(columns) {
  return el("div", { class: "profiles" }, columns.map((c) => {
    const card = el("div", { class: "profile" },
      el("div", { class: "pn", title: c.name }, el("span", { style: { overflow: "hidden", textOverflow: "ellipsis" } }, c.name), el("span", { class: `dtype ${dtypeClass(c.dtype)}` }, c.dtype)),
      el("div", { class: "ps" }, `${fmt(c.unique)} valeurs distinctes · ${c.missing ? `${fmt(c.missing)} manquantes` : "aucune manquante"}`));
    if (c.numeric && c.hist) {
      card.append(sparkHist(c.hist));
      card.append(el("div", { class: "ps", style: { margin: "4px 0 0" } }, `min ${fmt(c.min, 3)} · moy. ${fmt(c.mean, 3)} · max ${fmt(c.max, 3)} · σ ${fmt(c.std, 3)}`));
    } else if (c.top) {
      const mx = Math.max(...c.top.map((t) => t[1]));
      card.append(el("div", { class: "top" }, c.top.map(([k, n]) => el("div", {},
        el("span", { class: "k", title: k }, k), el("span", { class: "b", style: { width: `${Math.max(4, (n / mx) * 70)}px`, background: seriesColor(1) } }), el("span", { class: "v" }, fmt(n))))));
    }
    return card;
  }));
}

// ---------- Modèles ----------
async function loadModel(id, port) {
  const seq = ++reqSeq;
  actionsEl.replaceChildren(downloadBtn(id, port, "joblib", baseName(id)));
  try {
    const res = await api.port(id, port);
    if (seq !== reqSeq) return;
    bodyEl.replaceChildren(el("div", { class: "view" }, modelCard(res.summary)));
  } catch (e) {
    bodyEl.replaceChildren(el("div", { class: "bottom-empty" }, e.message));
  }
}

// ---------- Vues ----------
async function loadView(id) {
  const seq = ++reqSeq;
  actionsEl.replaceChildren();
  try {
    const res = await api.view(id);
    if (seq !== reqSeq) return;
    const v = el("div", { class: "view" });
    bodyEl.replaceChildren(v);
    renderBlocks(res.blocks, v);
  } catch (e) {
    bodyEl.replaceChildren(el("div", { class: "bottom-empty" }, e.message));
  }
}

