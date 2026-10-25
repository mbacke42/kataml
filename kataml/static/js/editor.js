// Éditeur de workflow : canevas zoomable, nœuds, connexions et annotations.

import { el, svg, icon, familyOf, contextMenu, fmt, searchScore } from "./ui.js";
import { t } from "./i18n.js";
import {
  store, spec, nodeById, annById, groupById, collapsedGroupOf, newId, commit, emit, on,
  displayState, missingConfig, wouldCycle, topoOrder,
} from "./state.js";

export const NODE_W = 184;
export const NODE_H = 64;
const view = { x: 60, y: 40, k: 1 };

let wrap, world, edgesSvg, nodesLayer, annLayer, selRect;
let drag = null;          // interaction en cours
let spaceDown = false;

// ---------- Coordonnées ----------
function toWorld(clientX, clientY) {
  const r = wrap.getBoundingClientRect();
  return { x: (clientX - r.left - view.x) / view.k, y: (clientY - r.top - view.y) / view.k };
}
function applyView() {
  world.style.transform = `translate(${view.x}px, ${view.y}px) scale(${view.k})`;
  wrap.style.backgroundSize = `${20 * view.k}px ${20 * view.k}px`;
  wrap.style.backgroundPosition = `${view.x}px ${view.y}px`;
  document.getElementById("zoom-label").textContent = `${Math.round(view.k * 100)} %`;
}
export function zoomBy(factor, cx, cy) {
  const r = wrap.getBoundingClientRect();
  cx ??= r.width / 2; cy ??= r.height / 2;
  const k = Math.min(2.5, Math.max(0.2, view.k * factor));
  view.x = cx - ((cx - view.x) * k) / view.k;
  view.y = cy - ((cy - view.y) * k) / view.k;
  view.k = k;
  applyView();
}
export function zoomReset() { zoomBy(1 / view.k); }
export function fitView() {
  const hidden = hiddenNodes();
  const items = [...store.wf.nodes.filter((n) => !hidden.has(n.id)).map((n) => [n.x, n.y, n.x + NODE_W, n.y + NODE_H]),
    ...collapsedGroups().map((g) => [g.x, g.y, g.x + NODE_W, g.y + groupHeight(g)]),
    ...(store.wf.annotations || []).map((a) => [a.x, a.y, a.x + a.w, a.y + a.h])];
  const r = wrap.getBoundingClientRect();
  if (!items.length) { view.x = 60; view.y = 40; view.k = 1; applyView(); return; }
  const x0 = Math.min(...items.map((i) => i[0])), y0 = Math.min(...items.map((i) => i[1]));
  const x1 = Math.max(...items.map((i) => i[2])), y1 = Math.max(...items.map((i) => i[3]));
  const k = Math.min(1.2, Math.max(0.25, Math.min((r.width - 100) / (x1 - x0), (r.height - 100) / (y1 - y0))));
  view.k = k;
  view.x = (r.width - (x1 - x0) * k) / 2 - x0 * k;
  view.y = (r.height - (y1 - y0) * k) / 2 - y0 * k;
  applyView();
}
export function viewCenter() {
  const r = wrap.getBoundingClientRect();
  return toWorld(r.left + r.width / 2, r.top + r.height / 2);
}

// ---------- Ports ----------
function portY(count, i) { return (NODE_H * (i + 1)) / (count + 1); }
function portPos(node, dir, i) {
  const g = collapsedGroupOf(node.id);
  if (g) {
    const ports = groupPorts(g)[dir === "in" ? "inputs" : "outputs"];
    const k = ports.findIndex((p) => p.node === node.id && p.port === i);
    const h = groupHeight(g);
    if (k < 0) return { x: g.x + NODE_W / 2, y: g.y + h / 2 };
    return { x: g.x + (dir === "in" ? -2 : NODE_W + 2), y: g.y + groupPortY(h, ports.length, k) };
  }
  const sp = spec(node.type);
  const count = dir === "in" ? sp?.inputs.length || 0 : sp?.outputs.length || 0;
  return { x: node.x + (dir === "in" ? -2 : NODE_W + 2), y: node.y + portY(count, i) };
}
function portKind(node, dir, i) {
  const sp = spec(node.type);
  return (dir === "in" ? sp?.inputs[i] : sp?.outputs[i])?.kind;
}

// ---------- Rendu ----------
export function render() {
  const hidden = hiddenNodes();
  nodesLayer.replaceChildren(...store.wf.nodes.filter((n) => !hidden.has(n.id)).map(nodeEl), ...collapsedGroups().map(groupEl));
  renderAnnotations();
  renderEdges();
  document.getElementById("canvas-empty").classList.toggle("hidden", store.wf.nodes.length > 0 || (store.wf.annotations || []).length > 0);
}

function nodeInfo(node, state) {
  const st = store.states[node.id];
  if (state === "executed") {
    const outs = (st.outputs || []).filter((o) => o.kind === "data");
    const parts = outs.slice(0, 2).map((o) => `${fmt(o.rows)} × ${o.cols}`);
    if (!parts.length && st.outputs?.some((o) => o.kind === "model")) parts.push("modèle entraîné");
    if (!parts.length && st.has_view) parts.push("vue disponible");
    return parts.join(" · ") + (st.seconds >= 0.5 ? ` · ${st.seconds.toFixed(1)} s` : "");
  }
  if (state === "error") return st?.message || "Erreur";
  if (state === "running") return "Exécution…";
  if (state === "queued") return "En attente…";
  if (state === "unconfigured") return missingConfig(node)[0] || "";
  return "Prêt";
}

function nodeEl(node) {
  const sp = spec(node.type);
  const fam = familyOf(sp);
  const state = displayState(node);
  const n = el("div", {
    class: `node${store.selection.has(node.id) ? " selected" : ""}`,
    dataset: { id: node.id, state },
    style: { left: `${node.x}px`, top: `${node.y}px` },
    title: sp ? `${sp.name} — ${sp.category}` : node.type,
  });
  n.append(
    el("div", { class: "head" },
      el("div", { class: "ico", style: { background: fam.color } }, icon(fam.icon, "")),
      el("div", { class: "titles" },
        el("div", { class: "title" }, sp?.name || node.type),
        el("div", { class: "label" }, node.label || `#${node.id.replace(/^n/, "")}`))),
    el("div", { class: "foot" },
      el("span", { class: "traffic", "aria-label": state }, el("i"), el("i"), el("i")),
      el("span", { class: "info" }, nodeInfo(node, state))),
    el("button", { class: "run-btn", title: "Exécuter (F7)", dataset: { run: node.id } }, icon("i-play", "")),
  );
  if (state === "error") n.append(el("div", { class: "err-badge", title: store.states[node.id]?.message }, icon("i-x")));
  (sp?.inputs || []).forEach((p, i) => {
    n.append(el("div", {
      class: `port in ${p.kind}${(sp.optional_inputs || []).includes(i) ? " optional" : ""}`,
      style: { top: `${portY(sp.inputs.length, i) - 7}px` },
      dataset: { dir: "in", port: i, kind: p.kind }, title: `Entrée : ${p.name}`,
    }));
  });
  (sp?.outputs || []).forEach((p, i) => {
    const o = store.states[node.id]?.outputs?.[i];
    const meta = o?.kind === "data" ? ` (${fmt(o.rows)} × ${o.cols})` : o?.kind === "model" ? ` (${o.name})` : "";
    n.append(el("div", {
      class: `port out ${p.kind}`,
      style: { top: `${portY(sp.outputs.length, i) - 7}px` },
      dataset: { dir: "out", port: i, kind: p.kind }, title: `Sortie : ${p.name}${meta} — clic pour afficher`,
    }));
  });
  return n;
}

export function refreshNode(id) {
  const g = collapsedGroupOf(id);
  if (g) { refreshGroup(g); return; }
  const node = nodeById(id);
  const old = nodesLayer.querySelector(`.node[data-id="${CSS.escape(id)}"]`);
  if (!node) { old?.remove(); return; }
  const fresh = nodeEl(node);
  if (old) old.replaceWith(fresh); else nodesLayer.append(fresh);
}
export function refreshAllNodes() {
  const hidden = hiddenNodes();
  for (const n of store.wf.nodes) if (!hidden.has(n.id)) refreshNode(n.id);
  for (const g of collapsedGroups()) refreshGroup(g);
  renderFrames();
  renderEdges();
}

function edgePath(a, b) {
  const dx = Math.max(40, Math.abs(b.x - a.x) * 0.5);
  return `M${a.x},${a.y} C${a.x + dx},${a.y} ${b.x - dx},${b.y} ${b.x},${b.y}`;
}

export function renderEdges() {
  const frag = [];
  store.wf.edges.forEach((e, idx) => {
    const a = nodeById(e.from), b = nodeById(e.to);
    if (!a || !b) return;
    const ga = collapsedGroupOf(a.id), gb = collapsedGroupOf(b.id);
    if (ga && ga === gb) return;
    // Pipeline contracté : les entrées masquées (recettes alimentées par la table brute) ne se dessinent pas.
    if (gb?.pipeline && !groupPorts(gb).inputs.some((p) => p.node === b.id && p.port === e.toPort)) return;
    const d = edgePath(portPos(a, "out", e.fromPort), portPos(b, "in", e.toPort));
    const kind = portKind(a, "out", e.fromPort);
    const running = store.states[e.to]?.state === "running";
    const sel = store.selectedEdge === idx;
    frag.push(svg("g", { class: sel ? "selected" : "", "data-edge": idx },
      svg("path", { class: "edge-hit", d, "data-edge": idx }),
      svg("path", { class: `edge ${kind || ""}`, d }),
      running ? svg("path", { class: "flow", d }) : null));
  });
  if (drag?.type === "connect" && drag.cur) {
    const a = drag.anchor, b = drag.cur;
    const d = drag.dir === "out" ? edgePath(a, b) : edgePath(b, a);
    frag.push(svg("path", { class: `edge ghost${drag.bad ? " bad" : ""}`, d }));
  }
  edgesSvg.replaceChildren(...frag);
}

function renderAnnotations() {
  annLayer.replaceChildren(...expandedGroups().map(frameEl).filter(Boolean), ...(store.wf.annotations || []).map(annEl));
}
function renderFrames() {
  annLayer.querySelectorAll(".group-frame").forEach((f) => f.remove());
  annLayer.prepend(...expandedGroups().map(frameEl).filter(Boolean));
}

// ---------- Groupes (composants) ----------
const groups = () => store.wf.groups || (store.wf.groups = []);
const collapsedGroups = () => groups().filter((g) => g.collapsed);
const expandedGroups = () => groups().filter((g) => !g.collapsed);
function hiddenNodes() {
  return new Set(collapsedGroups().flatMap((g) => g.nodes));
}

// Ports d'un groupe : entrées non alimentées de l'intérieur, sorties non consommées
// uniquement à l'intérieur.
export function groupPorts(g) {
  const inside = new Set(g.nodes);
  const inputs = [], outputs = [];
  const members = g.nodes.map(nodeById).filter(Boolean).sort((a, b) => a.y - b.y || a.x - b.x);
  for (const n of members) {
    const sp = spec(n.type);
    if (!sp) continue;
    sp.inputs.forEach((p, i) => {
      const e = store.wf.edges.find((ed) => ed.to === n.id && ed.toPort === i);
      if (!e || !inside.has(e.from)) inputs.push({ node: n.id, port: i, kind: p.kind, name: `${p.name} · ${n.label || sp.name}`, optional: (sp.optional_inputs || []).includes(i) });
    });
    sp.outputs.forEach((p, i) => {
      const uses = store.wf.edges.filter((ed) => ed.from === n.id && ed.fromPort === i);
      if (!uses.length || uses.some((ed) => !inside.has(ed.to))) outputs.push({ node: n.id, port: i, kind: p.kind, name: `${p.name} · ${n.label || sp.name}` });
    });
  }
  if (g.pipeline) {
    // Pipeline contracté : seule compte la table brute ; on masque les ports optionnels libres
    // et les entrées des recettes alimentées par la même table.
    const raw = store.wf.edges.find((ed) => ed.to === g.pipeline && ed.toPort === 0);
    const same = (p) => { const e = store.wf.edges.find((ed) => ed.to === p.node && ed.toPort === p.port);
      return e && raw && e.from === raw.from && e.fromPort === raw.fromPort; };
    const isRaw = (p) => p.node === g.pipeline && p.port === 0;
    const linked = (p) => store.wf.edges.some((ed) => ed.to === p.node && ed.toPort === p.port);
    return { inputs: inputs.filter((p) => isRaw(p) || (linked(p) && !same(p))), outputs };
  }
  return { inputs, outputs };
}
function groupHeight(g) {
  const { inputs, outputs } = groupPorts(g);
  return Math.max(NODE_H, 26 + 18 * Math.max(inputs.length, outputs.length));
}
function groupPortY(h, count, k) { return (h * (k + 1)) / (count + 1); }

export function groupState(g) {
  const states = g.nodes.map(nodeById).filter(Boolean).map(displayState);
  for (const s of ["running", "queued", "error", "unconfigured"]) if (states.includes(s)) return s;
  return states.length && states.every((s) => s === "executed") ? "executed" : "configured";
}

function groupEl(g) {
  const { inputs, outputs } = groupPorts(g);
  const h = groupHeight(g);
  const state = groupState(g);
  const done = g.nodes.filter((id) => store.states[id]?.state === "executed").length;
  const n = el("div", {
    class: `node group-node${store.selection.has(g.id) ? " selected" : ""}`,
    dataset: { id: g.id, state, group: g.id },
    style: { left: `${g.x}px`, top: `${g.y}px`, height: `${h}px` },
    title: g.pipeline ? `Pipeline contracté : ${pipelineSteps(g.pipeline).join(" → ")} (double-clic pour déplier)`
      : `${g.name} — composant de ${g.nodes.length} nœuds (double-clic pour déplier)`,
  },
  el("div", { class: "head" },
    el("div", { class: "ico", style: { background: g.pipeline ? "var(--c-compose)" : "var(--c-group)" } }, icon(g.pipeline ? "c-compose" : "c-group", "")),
    el("div", { class: "titles" }, el("div", { class: "title" }, g.name),
      el("div", { class: "label" }, g.pipeline ? pipelineSteps(g.pipeline).join(" → ") : t("{n} nœuds · composant", { n: g.nodes.length })))),
  el("div", { class: "foot" },
    el("span", { class: "traffic" }, el("i"), el("i"), el("i")),
    el("span", { class: "info" }, state === "executed" ? "Exécuté" : `${done}/${g.nodes.length} exécutés`)),
  el("button", { class: "run-btn", title: "Exécuter le composant (F7)", dataset: { run: g.id } }, icon("i-play", "")));
  inputs.forEach((p, k) => n.append(el("div", {
    class: `port in ${p.kind}${p.optional ? " optional" : ""}`, style: { top: `${groupPortY(h, inputs.length, k) - 7}px` },
    dataset: { dir: "in", port: p.port, kind: p.kind, member: p.node }, title: `Entrée : ${p.name}` })));
  outputs.forEach((p, k) => n.append(el("div", {
    class: `port out ${p.kind}`, style: { top: `${groupPortY(h, outputs.length, k) - 7}px` },
    dataset: { dir: "out", port: p.port, kind: p.kind, member: p.node }, title: `Sortie : ${p.name} — clic pour afficher` })));
  return n;
}
function refreshGroup(g) {
  const old = nodesLayer.querySelector(`.node[data-id="${CSS.escape(g.id)}"]`);
  const fresh = groupEl(g);
  if (old) old.replaceWith(fresh); else nodesLayer.append(fresh);
}

function frameEl(g) {
  const members = g.nodes.map(nodeById).filter(Boolean);
  if (!members.length) return null;
  const x0 = Math.min(...members.map((m) => m.x)) - 18, y0 = Math.min(...members.map((m) => m.y)) - 40;
  const x1 = Math.max(...members.map((m) => m.x + NODE_W)) + 18, y1 = Math.max(...members.map((m) => m.y + NODE_H)) + 18;
  return el("div", { class: "group-frame", dataset: { frame: g.id }, style: { left: `${x0}px`, top: `${y0}px`, width: `${x1 - x0}px`, height: `${y1 - y0}px` } },
    el("div", { class: "group-head", dataset: { framehead: g.id }, title: "Glisser pour déplacer le composant" },
      icon(g.pipeline ? "c-compose" : "c-group", "i"), el("span", { class: "gname" }, g.name),
      el("button", { class: "btn ghost sm", dataset: { collapse: g.id }, title: "Réduire en un seul nœud" }, "Réduire")));
}

export function createGroup(ids, name = "Composant") {
  const nodes = ids.filter((id) => nodeById(id) && !groups().some((g) => g.nodes.includes(id)));
  if (nodes.length < 2) return null;
  const members = nodes.map(nodeById);
  const g = { id: newId("g"), name, nodes, collapsed: true,
    x: Math.round(members.reduce((a, m) => a + m.x, 0) / members.length / 10) * 10,
    y: Math.round(members.reduce((a, m) => a + m.y, 0) / members.length / 10) * 10 };
  groups().push(g);
  commit("structure");
  render();
  select([g.id]);
  return g;
}
export function toggleGroup(id, collapsed = null) {
  const g = groupById(id);
  if (!g) return;
  g.collapsed = collapsed ?? !g.collapsed;
  commit("layout");
  render();
  select(g.collapsed ? [g.id] : g.nodes);
}
export function ungroup(id) {
  const g = groupById(id);
  if (!g) return;
  store.wf.groups = groups().filter((x) => x !== g);
  commit("structure");
  render();
  select(g.nodes);
}
export function renameGroup(id, name) {
  const g = groupById(id);
  if (!g || !name) return;
  g.name = name;
  commit("label");
  render();
}
// Description autonome d'un groupe, pour l'enregistrer comme composant réutilisable.
export function groupAsComponent(id) {
  const g = groupById(id);
  const inside = new Set(g.nodes);
  const nodes = structuredClone(g.nodes.map(nodeById).filter(Boolean));
  const x0 = Math.min(...nodes.map((n) => n.x)), y0 = Math.min(...nodes.map((n) => n.y));
  for (const n of nodes) { n.x -= x0; n.y -= y0; }
  return { version: 1, name: g.name, description: g.description || "", nodes,
    edges: store.wf.edges.filter((e) => inside.has(e.from) && inside.has(e.to)) };
}
export function insertComponent(comp, at) {
  const pos = at || viewCenter();
  const map = {};
  for (const n of comp.nodes) {
    const id = newId("n");
    map[n.id] = id;
    store.wf.nodes.push({ ...structuredClone(n), id, x: Math.round(pos.x + n.x), y: Math.round(pos.y + n.y) });
  }
  for (const e of comp.edges || []) if (map[e.from] && map[e.to]) store.wf.edges.push({ ...e, from: map[e.from], to: map[e.to] });
  const g = { id: newId("g"), name: comp.name || "Composant", nodes: Object.values(map), collapsed: true,
    x: Math.round(pos.x - NODE_W / 2), y: Math.round(pos.y - NODE_H / 2) };
  groups().push(g);
  commit("structure");
  render();
  select([g.id]);
  return g;
}

// ---------- Organisation automatique ----------
// Disposition en couches : chaque nœud est placé une colonne après son prédécesseur
// le plus profond, l'ordre vertical suivant la moyenne des prédécesseurs.
export function autoLayout(ids = null) {
  // Unités placées : nœuds visibles et groupes réduits (un groupe compte pour un nœud).
  const unitOf = (nid) => collapsedGroupOf(nid)?.id || nid;
  let units = new Set((ids || []).map((id) => (nodeById(id) ? unitOf(id) : id)).filter((id) => nodeById(id) || groupById(id)));
  if (units.size < 2) units = new Set([...store.wf.nodes.map((n) => unitOf(n.id))]);
  if (units.size < 2) return;
  const pos = (u) => groupById(u) || nodeById(u);
  const links = [];
  for (const e of store.wf.edges) {
    const a = unitOf(e.from), b = unitOf(e.to);
    if (a !== b && units.has(a) && units.has(b)) links.push([a, b]);
  }
  // Ordre topologique des unités.
  const indeg = new Map([...units].map((u) => [u, 0]));
  links.forEach(([, b]) => indeg.set(b, indeg.get(b) + 1));
  const ready = [...units].filter((u) => !indeg.get(u)).sort((a, b) => pos(a).y - pos(b).y);
  const order = [];
  while (ready.length) {
    const u = ready.shift();
    order.push(u);
    links.filter(([a]) => a === u).forEach(([, b]) => { indeg.set(b, indeg.get(b) - 1); if (!indeg.get(b)) ready.push(b); });
  }
  const layer = {};
  for (const u of order) {
    const preds = links.filter(([, b]) => b === u).map(([a]) => layer[a] + 1);
    layer[u] = preds.length ? Math.max(...preds) : 0;
  }
  const x0 = Math.min(...order.map((u) => pos(u).x)), y0 = Math.min(...order.map((u) => pos(u).y));
  const byLayer = [];
  for (const u of order) (byLayer[layer[u]] ||= []).push(u);
  const rank = {};
  byLayer.forEach((list, L) => {
    if (L) {
      const bary = (u) => {
        const ps = links.filter(([, b]) => b === u).map(([a]) => rank[a]);
        return ps.length ? ps.reduce((x, y) => x + y, 0) / ps.length : 0;
      };
      list.sort((a, b) => bary(a) - bary(b));
    }
    list.forEach((u, k) => { rank[u] = k; });
  });
  const rowH = NODE_H + 46;
  const tallest = Math.max(...byLayer.map((l) => l.length));
  byLayer.forEach((list, L) => {
    const offset = ((tallest - list.length) * rowH) / 2;
    list.forEach((u, k) => {
      const it = pos(u);
      const nx = Math.round((x0 + L * (NODE_W + 96)) / 10) * 10, ny = Math.round((y0 + offset + k * rowH) / 10) * 10;
      const g = groupById(u);
      if (g) g.nodes.map(nodeById).filter(Boolean).forEach((m) => { m.x += nx - it.x; m.y += ny - it.y; });
      it.x = nx; it.y = ny;
    });
  });
  commit("layout");
  render();
  setTimeout(fitView, 20);
}

// ---------- Création d'un Pipeline depuis la sélection ----------
const isTransformer = (n) => /^(sk\.transformer|text|meta\.(RFE|RFECV|SelectFromModel|SequentialFeatureSelector))\./.test(n.type) || /^sk\.transformer\.|^text\./.test(n.type);
const isSupervised = (n) => /^sk\.(classifier|regressor)\.|^meta\.(Voting|Stacking|OneVs|OutputCode|FixedThreshold|TunedThreshold)/.test(n.type);
export function pipelinePlan(ids) {
  const nodes = ids.map(nodeById).filter(Boolean);
  const learners = nodes.filter(isSupervised);
  const preps = nodes.filter(isTransformer);
  if (learners.length !== 1 || !preps.length || preps.length > 3) return null;
  const order = topoOrder(preps.map((n) => n.id));
  const first = nodeById(order[0]);
  const rawEdge = store.wf.edges.find((e) => e.to === first.id && e.toPort === 0);
  if (!rawEdge) return null;
  const outPort = (n) => spec(n.type).outputs.findIndex((o) => o.kind === "model");
  return { learner: learners[0], preps: order.map(nodeById), raw: rawEdge, outPort };
}
export function createPipeline(ids, { contract = true } = {}) {
  const plan = pipelinePlan(ids);
  if (!plan) return null;
  const { learner, preps, raw, outPort } = plan;
  const node = { id: newId("n"), type: "compose.pipeline", x: learner.x + NODE_W + 90, y: learner.y, params: {}, label: "" };
  avoidOverlap(node);
  store.wf.nodes.push(node);
  store.wf.edges.push({ from: raw.from, fromPort: raw.fromPort, to: node.id, toPort: 0 });
  store.wf.edges.push({ from: learner.id, fromPort: outPort(learner), to: node.id, toPort: 1 });
  preps.forEach((p, k) => store.wf.edges.push({ from: p.id, fromPort: outPort(p), to: node.id, toPort: 2 + k }));
  commit("structure");
  render();
  select([node.id]);
  ensureVisible(node);
  if (contract) contractPipeline(node.id);
  return node;
}

// ---------- Validation croisée d'un modèle entraîné sur une table transformée ----------
// Les nœuds d'évaluation par validation croisée réentraînent le modèle sur chaque pli, mais
// pas les prétraitements placés en amont : il faut les réunir dans un Pipeline.
const CV_TYPES = new Set(["tune.cross_validation", "tune.compare", "tune.grid_search", "tune.learning_curve",
  "tune.validation_curve", "tune.permutation_test", "tune.cross_val_predict"]);
const edgeTo = (id, port) => store.wf.edges.find((e) => e.to === id && e.toPort === port);
function prepChain(modelId) {
  const chain = [];
  let e = edgeTo(modelId, 0);
  while (e && chain.length < 3) {
    const src = nodeById(e.from);
    if (!src || !isTransformer(src) || e.fromPort !== 0) break;
    chain.unshift(src);
    e = edgeTo(src.id, 0);
  }
  return chain;
}
export function leakyCvInputs(nodeId) {
  const n = nodeById(nodeId);
  if (!n || !CV_TYPES.has(n.type)) return [];
  const out = [];
  spec(n.type).inputs.forEach((p, i) => {
    const e = p.kind === "model" && edgeTo(nodeId, i);
    const model = e && nodeById(e.from);
    if (!model || !isSupervised(model)) return;
    const chain = prepChain(model.id);
    if (chain.length && edgeTo(chain[0].id, 0)) out.push({ port: i, model, chain });
  });
  return out;
}
// Crée le Pipeline (prétraitements + modèle), le branche à la place du modèle et, si la
// table évaluée était une table transformée, la remplace par la table brute.
export function pipelineForCv(nodeId, port) {
  const item = leakyCvInputs(nodeId).find((x) => x.port === port);
  if (!item) return null;
  const { model, chain } = item;
  const raw = edgeTo(chain[0].id, 0);
  const pipe = createPipeline([...chain.map((c) => c.id), model.id], { contract: false });
  if (!pipe) return null;
  store.wf.edges = store.wf.edges.filter((e) => !(e.to === nodeId && e.toPort === port));
  store.wf.edges.push({ from: pipe.id, fromPort: 0, to: nodeId, toPort: port });
  const tPort = spec(nodeById(nodeId).type).inputs.findIndex((p) => p.kind === "data");
  const te = edgeTo(nodeId, tPort);
  if (te && chain.some((c) => c.id === te.from)) Object.assign(te, { from: raw.from, fromPort: raw.fromPort });
  commit("structure");
  render();
  const g = contractPipeline(pipe.id);
  if (g) {
    // Au-dessus de la ligne table → validation croisée, pour que les connexions ne se cachent pas.
    g.y = model.y - NODE_H - 50;
    commit("layout");
    render();
  }
  return pipe;
}

// ---------- Pipeline contracté ----------
// Un Pipeline et ses nœuds « recette » (prétraitements et modèle branchés sur ses ports)
// forment un composant réduit : le canevas reste lisible, double-clic pour le déplier.
function pipelineMembers(pid) {
  return [...new Set(store.wf.edges.filter((e) => e.to === pid && e.toPort >= 1).map((e) => e.from))];
}
export function pipelineSteps(pid) {
  const name = (id) => { const n = nodeById(id); return n ? (n.label || spec(n.type)?.name || n.type) : "?"; };
  const at = (port) => store.wf.edges.find((e) => e.to === pid && e.toPort === port);
  const preps = [2, 3, 4].map(at).filter(Boolean).map((e) => name(e.from));
  const model = at(1);
  return [...preps, ...(model ? [name(model.from)] : [])];
}
export function canContractPipeline(pid) {
  const n = nodeById(pid);
  if (!n || n.type !== "compose.pipeline") return false;
  const ids = [pid, ...pipelineMembers(pid)];
  return ids.length > 1 && !ids.some((id) => groups().some((g) => g.nodes.includes(id)));
}
export function contractPipeline(pid) {
  if (!canContractPipeline(pid)) return null;
  const p = nodeById(pid);
  const g = createGroup([pid, ...pipelineMembers(pid)], "Pipeline");
  if (!g) return null;
  // À la place du modèle : le Pipeline apparaît là où étaient ses étapes.
  const model = nodeById(store.wf.edges.find((e) => e.to === pid && e.toPort === 1)?.from) || p;
  Object.assign(g, { pipeline: pid, x: model.x, y: model.y });
  commit("structure");
  render();
  select([g.id]);
  return g;
}

const ANN_COLORS = {
  jaune: "color-mix(in oklab, #f5c84c 28%, var(--panel))",
  bleu: "color-mix(in oklab, #2a78d6 16%, var(--panel))",
  vert: "color-mix(in oklab, #1baf7a 18%, var(--panel))",
  rose: "color-mix(in oklab, #e87ba4 20%, var(--panel))",
  gris: "color-mix(in oklab, #898781 14%, var(--panel))",
};

function annEl(a) {
  const d = el("div", {
    class: `annotation${store.selection.has(a.id) ? " selected" : ""}`,
    dataset: { ann: a.id },
    style: { left: `${a.x}px`, top: `${a.y}px`, width: `${a.w}px`, height: `${a.h}px`, background: ANN_COLORS[a.color] || ANN_COLORS.jaune },
    title: "Double-clic pour modifier",
  });
  const [first, ...rest] = (a.text || "").split("\n");
  d.append(el("span", { class: "ann-title" }, first), rest.length ? "\n" + rest.join("\n") : "", el("div", { class: "resize", dataset: { resize: a.id } }));
  return d;
}

function editAnnotation(a) {
  const d = annLayer.querySelector(`[data-ann="${CSS.escape(a.id)}"]`);
  if (!d) return;
  const ta = el("textarea", { spellcheck: "false" });
  ta.value = a.text || "";
  d.replaceChildren(ta);
  ta.focus();
  ta.addEventListener("mousedown", (e) => e.stopPropagation());
  ta.addEventListener("keydown", (e) => { e.stopPropagation(); if (e.key === "Escape") ta.blur(); });
  ta.addEventListener("blur", () => { a.text = ta.value; commit("annotation"); renderAnnotations(); });
}

export function addAnnotation(at) {
  const c = at || viewCenter();
  const a = { id: newId("a"), x: Math.round(c.x - 140), y: Math.round(c.y - 50), w: 280, h: 100, color: "jaune", text: "Annotation\nDouble-cliquez pour modifier." };
  store.wf.annotations = [...(store.wf.annotations || []), a];
  commit("annotation");
  renderAnnotations();
  select([a.id]);
  setTimeout(() => editAnnotation(a), 20);
}

// ---------- Sélection ----------
export function select(ids, additive = false) {
  if (!additive) store.selection.clear();
  for (const id of ids) store.selection.add(id);
  store.selectedEdge = null;
  syncSelection();
}
function syncSelection() {
  nodesLayer.querySelectorAll(".node").forEach((n) => n.classList.toggle("selected", store.selection.has(n.dataset.id)));
  annLayer.querySelectorAll(".annotation").forEach((n) => n.classList.toggle("selected", store.selection.has(n.dataset.ann)));
  renderEdges();
  emit("selection");
}

// ---------- Ajout / suppression ----------
export function addNode(type, at, connectFrom = null) {
  const sp = spec(type);
  if (!sp) return null;
  const pos = at || viewCenter();
  const node = { id: newId("n"), type, x: Math.round(pos.x - NODE_W / 2), y: Math.round(pos.y - NODE_H / 2), params: {}, label: "" };
  // Valeurs par défaut des paramètres non hyperparamètres.
  for (const p of sp.params) if (p.group !== "Hyperparamètres" && p.default !== undefined && p.default !== null) node.params[p.name] = structuredClone(p.default);
  avoidOverlap(node);
  store.wf.nodes.push(node);
  if (connectFrom) autoConnect(connectFrom, node);
  commit("structure");
  render();
  select([node.id]);
  ensureVisible(node);
  return node;
}

// Déplace la vue si le nœud est hors de l'écran.
export function ensureVisible(node) {
  const r = wrap.getBoundingClientRect();
  const sx = node.x * view.k + view.x, sy = node.y * view.k + view.y;
  const sw = NODE_W * view.k, sh = NODE_H * view.k, pad = 40;
  let dx = 0, dy = 0;
  if (sx < pad) dx = pad - sx; else if (sx + sw > r.width - pad) dx = r.width - pad - sx - sw;
  if (sy < pad) dy = pad - sy; else if (sy + sh > r.height - pad) dy = r.height - pad - sy - sh;
  if (dx || dy) { view.x += dx; view.y += dy; applyView(); }
}

function avoidOverlap(node) {
  for (let tries = 0; tries < 30; tries++) {
    const hit = store.wf.nodes.find((n) => Math.abs(n.x - node.x) < NODE_W - 20 && Math.abs(n.y - node.y) < NODE_H + 10);
    if (!hit) return;
    node.y = hit.y + NODE_H + 30;
  }
}

// Relie automatiquement le nœud source à la première entrée compatible.
function autoConnect(src, node) {
  const sNode = typeof src === "string" ? nodeById(src) : nodeById(src.node);
  if (!sNode) return;
  const sOut = spec(sNode.type)?.outputs || [];
  const tIn = spec(node.type)?.inputs || [];
  const outIdx = typeof src === "object" && src.port !== undefined ? [src.port] : sOut.map((_, i) => i);
  for (const oi of outIdx) {
    const ii = tIn.findIndex((p, k) => p.kind === sOut[oi]?.kind && !store.wf.edges.some((e) => e.to === node.id && e.toPort === k));
    if (ii >= 0) { connect(sNode.id, oi, node.id, ii, false); return; }
  }
}

export function connect(from, fromPort, to, toPort, doCommit = true) {
  const a = nodeById(from), b = nodeById(to);
  if (!a || !b) return false;
  if (portKind(a, "out", fromPort) !== portKind(b, "in", toPort)) return false;
  if (wouldCycle(from, to)) return false;
  store.wf.edges = store.wf.edges.filter((e) => !(e.to === to && e.toPort === toPort));
  store.wf.edges.push({ from, fromPort, to, toPort });
  if (doCommit) { commit("structure"); refreshNode(to); renderEdges(); }
  return true;
}

export function deleteSelection() {
  if (store.selectedEdge !== null) {
    const e = store.wf.edges[store.selectedEdge];
    store.wf.edges.splice(store.selectedEdge, 1);
    store.selectedEdge = null;
    commit("structure");
    if (e) refreshNode(e.to);
    renderEdges();
    emit("selection");
    return;
  }
  if (!store.selection.size) return;
  const ids = new Set(store.selection);
  for (const g of groups()) if (ids.has(g.id)) g.nodes.forEach((id) => ids.add(id));
  store.wf.groups = groups().filter((g) => !ids.has(g.id)).map((g) => ({ ...g, nodes: g.nodes.filter((id) => !ids.has(id)) }))
    .filter((g) => g.nodes.length >= 1);
  store.wf.nodes = store.wf.nodes.filter((n) => !ids.has(n.id));
  store.wf.annotations = (store.wf.annotations || []).filter((a) => !ids.has(a.id));
  store.wf.edges = store.wf.edges.filter((e) => !ids.has(e.from) && !ids.has(e.to));
  for (const id of ids) delete store.states[id];
  store.selection = new Set();
  commit("structure");
  render();
  emit("selection");
}

// ---------- Presse-papiers ----------
let clipboard = null;
export function copySelection() {
  const ids = new Set(store.selection);
  const grps = groups().filter((g) => ids.has(g.id));
  grps.forEach((g) => g.nodes.forEach((id) => ids.add(id)));
  const nodes = store.wf.nodes.filter((n) => ids.has(n.id));
  const anns = (store.wf.annotations || []).filter((a) => ids.has(a.id));
  if (!nodes.length && !anns.length) return false;
  clipboard = JSON.parse(JSON.stringify({
    nodes, annotations: anns, groups: grps,
    edges: store.wf.edges.filter((e) => ids.has(e.from) && ids.has(e.to)),
  }));
  try { localStorage.setItem("kataml.clipboard", JSON.stringify(clipboard)); } catch { /* indisponible */ }
  return true;
}
export function paste(offset = 40) {
  let clip = clipboard;
  if (!clip) { try { clip = JSON.parse(localStorage.getItem("kataml.clipboard")); } catch { clip = null; } }
  if (!clip) return;
  const map = {};
  const ids = [];
  for (const n of clip.nodes) {
    const id = newId("n");
    map[n.id] = id;
    store.wf.nodes.push({ ...structuredClone(n), id, x: n.x + offset, y: n.y + offset });
    ids.push(id);
  }
  for (const a of clip.annotations || []) {
    const id = newId("a");
    store.wf.annotations = [...(store.wf.annotations || []), { ...structuredClone(a), id, x: a.x + offset, y: a.y + offset }];
    ids.push(id);
  }
  for (const e of clip.edges) store.wf.edges.push({ ...e, from: map[e.from], to: map[e.to] });
  for (const g of clip.groups || []) {
    const id = newId("g");
    groups().push({ ...structuredClone(g), id, nodes: g.nodes.map((n) => map[n]).filter(Boolean), x: g.x + offset, y: g.y + offset });
    ids.splice(0, ids.length, ...ids.filter((x) => !g.nodes.map((n) => map[n]).includes(x)), id);
  }
  clipboard = { ...clip, nodes: clip.nodes.map((n) => ({ ...n, x: n.x + offset, y: n.y + offset })),
    groups: (clip.groups || []).map((g) => ({ ...g, x: g.x + offset, y: g.y + offset })),
    annotations: (clip.annotations || []).map((a) => ({ ...a, x: a.x + offset, y: a.y + offset })) };
  commit("structure");
  render();
  select(ids);
}

// ---------- Ajout rapide (recherche flottante) ----------
let quickEl = null;
export function quickAdd(clientX, clientY, from = null) {
  closeQuick();
  const at = toWorld(clientX, clientY);
  const kind = from?.kind || null;
  const all = [...store.catalog.values()].filter((s) => !kind || s.inputs.some((p) => p.kind === kind));
  const input = el("input", { class: "field-input", placeholder: kind ? `Nœud acceptant ${kind === "model" ? "un modèle" : "une table"}…` : "Ajouter un nœud…" });
  const list = el("div", { class: "colpick-list", style: { maxHeight: "260px" } });
  quickEl = el("div", { class: "ctxmenu", style: { left: `${clientX}px`, top: `${clientY}px`, width: "300px", padding: "8px" } }, input, list);
  document.body.append(quickEl);
  let active = 0, results = [];
  const draw = () => {
    const q = input.value.trim().toLowerCase();
    results = all.map((s) => [s, searchScore(s, q)]).filter(([, sc]) => sc > 0)
      .sort((a, b) => b[1] - a[1] || a[0].name.localeCompare(b[0].name, "fr")).map(([s]) => s).slice(0, 40);
    active = Math.min(active, Math.max(0, results.length - 1));
    list.replaceChildren(...results.map((s, i) => {
      const fam = familyOf(s);
      return el("button", {
        class: i === active ? "on" : "", style: i === active ? { background: "var(--accent-soft)" } : {},
        onmousedown: (e) => { e.preventDefault(); pick(s); },
      }, el("span", { class: "cat-dot", style: { background: fam.color } }, icon(fam.icon, "")), s.name,
      el("span", { class: "k" }, s.family || s.category));
    }));
  };
  const pick = (s) => {
    closeQuick();
    const node = addNode(s.type, { x: at.x + NODE_W / 2, y: at.y }, from ? { node: from.node, port: from.port } : null);
    if (node && from && from.dir === "in") {
      // Connexion tirée depuis une entrée : on relie la sortie du nouveau nœud.
      const oi = spec(node.type).outputs.findIndex((p) => p.kind === from.kind);
      if (oi >= 0) connect(node.id, oi, from.node, from.port);
    }
  };
  input.addEventListener("input", () => { active = 0; draw(); });
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { active = Math.min(results.length - 1, active + 1); draw(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { active = Math.max(0, active - 1); draw(); e.preventDefault(); }
    else if (e.key === "Enter" && results[active]) pick(results[active]);
    else if (e.key === "Escape") closeQuick();
    e.stopPropagation();
  });
  input.addEventListener("blur", () => setTimeout(closeQuick, 120));
  draw();
  const r = quickEl.getBoundingClientRect();
  quickEl.style.left = `${Math.min(clientX, innerWidth - r.width - 8)}px`;
  quickEl.style.top = `${Math.min(clientY, innerHeight - 330)}px`;
  input.focus();
}
function closeQuick() { quickEl?.remove(); quickEl = null; }

// ---------- Interactions souris ----------
function onMouseDown(e) {
  if (e.button === 2) return;
  wrap.focus({ preventScroll: true });
  const t = e.target;
  const middle = e.button === 1 || (e.button === 0 && spaceDown);
  if (middle) { startPan(e); return; }

  const runBtn = t.closest("[data-run]");
  if (runBtn) { e.stopPropagation(); emit("execute", [runBtn.dataset.run]); return; }

  const port = t.closest(".port");
  if (port) {
    const nodeId = port.dataset.member || port.closest(".node").dataset.id;
    const dir = port.dataset.dir, idx = +port.dataset.port, kind = port.dataset.kind;
    const node = nodeById(nodeId);
    // Entrée déjà connectée : on détache la connexion pour la déplacer.
    if (dir === "in") {
      const ex = store.wf.edges.find((ed) => ed.to === nodeId && ed.toPort === idx);
      if (ex) {
        store.wf.edges = store.wf.edges.filter((ed) => ed !== ex);
        refreshNode(nodeId);
        const src = nodeById(ex.from);
        drag = { type: "connect", dir: "out", node: ex.from, port: ex.fromPort, kind, anchor: portPos(src, "out", ex.fromPort), detached: true, moved: true };
        drag.cur = toWorld(e.clientX, e.clientY);
        highlightTargets();
        renderEdges();
        return;
      }
    }
    drag = { type: "connect", dir, node: nodeId, port: idx, kind, anchor: portPos(node, dir, idx), startX: e.clientX, startY: e.clientY };
    highlightTargets();
    return;
  }

  const resize = t.closest("[data-resize]");
  if (resize) {
    const a = annById(resize.dataset.resize);
    drag = { type: "resize", ann: a, sx: e.clientX, sy: e.clientY, w: a.w, h: a.h };
    return;
  }

  const collapseBtn = t.closest("[data-collapse]");
  if (collapseBtn) { e.stopPropagation(); toggleGroup(collapseBtn.dataset.collapse, true); return; }
  const frameHead = t.closest("[data-framehead]");
  if (frameHead) {
    const g = groupById(frameHead.dataset.framehead);
    select(g.nodes);
    const items = g.nodes.map(nodeById).filter(Boolean);
    drag = { type: "move", start: toWorld(e.clientX, e.clientY), items, orig: items.map((it) => [it.x, it.y]), moved: false, sx: e.clientX, sy: e.clientY };
    return;
  }
  const nodeDiv = t.closest(".node");
  const annDiv = t.closest(".annotation");
  if (nodeDiv || annDiv) {
    if (annDiv && t.tagName === "TEXTAREA") return;
    const id = nodeDiv ? nodeDiv.dataset.id : annDiv.dataset.ann;
    if (e.shiftKey || e.ctrlKey || e.metaKey) {
      if (store.selection.has(id)) store.selection.delete(id); else store.selection.add(id);
      store.selectedEdge = null;
      syncSelection();
    } else if (!store.selection.has(id)) {
      select([id]);
    }
    const start = toWorld(e.clientX, e.clientY);
    const items = [...store.selection].flatMap((sid) => {
      const g = groupById(sid);
      return g ? [g, ...g.nodes.map(nodeById)] : [nodeById(sid) || annById(sid)];
    }).filter(Boolean);
    drag = { type: "move", start, items, orig: items.map((it) => [it.x, it.y]), moved: false, sx: e.clientX, sy: e.clientY };
    return;
  }

  const edgeHit = t.closest("[data-edge]");
  if (edgeHit) {
    store.selection.clear();
    store.selectedEdge = +edgeHit.dataset.edge;
    syncSelection();
    return;
  }

  if (e.shiftKey) {
    drag = { type: "select", sx: e.clientX, sy: e.clientY, base: new Set(store.selection) };
    return;
  }
  startPan(e, true);
}

function startPan(e, clearOnClick = false) {
  drag = { type: "pan", sx: e.clientX, sy: e.clientY, vx: view.x, vy: view.y, moved: false, clearOnClick };
  wrap.classList.add("panning");
}

function highlightTargets() {
  const wantDir = drag.dir === "out" ? "in" : "out";
  nodesLayer.querySelectorAll(".port").forEach((p) => {
    const nid = p.dataset.member || p.closest(".node").dataset.id;
    const ok = p.dataset.dir === wantDir && p.dataset.kind === drag.kind && nid !== drag.node &&
      !(wantDir === "in" ? wouldCycle(drag.node, nid) : wouldCycle(nid, drag.node));
    p.classList.toggle("dim", !ok && p.dataset.dir === wantDir);
  });
}
function clearTargets() {
  nodesLayer.querySelectorAll(".port").forEach((p) => p.classList.remove("dim", "target", "ok"));
}

function onMouseMove(e) {
  if (!drag) return;
  if (drag.type === "pan") {
    const dx = e.clientX - drag.sx, dy = e.clientY - drag.sy;
    if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true;
    view.x = drag.vx + dx; view.y = drag.vy + dy;
    applyView();
  } else if (drag.type === "move") {
    const p = toWorld(e.clientX, e.clientY);
    const dx = p.x - drag.start.x, dy = p.y - drag.start.y;
    if (!drag.moved && Math.abs(e.clientX - drag.sx) + Math.abs(e.clientY - drag.sy) < 3) return;
    drag.moved = true;
    const snap = e.altKey ? 1 : 10;
    drag.items.forEach((it, i) => {
      it.x = Math.round((drag.orig[i][0] + dx) / snap) * snap;
      it.y = Math.round((drag.orig[i][1] + dy) / snap) * snap;
      const div = nodesLayer.querySelector(`[data-id="${CSS.escape(it.id)}"]`) || annLayer.querySelector(`[data-ann="${CSS.escape(it.id)}"]`);
      if (div) { div.style.left = `${it.x}px`; div.style.top = `${it.y}px`; div.classList.add("dragging"); }
    });
    if (expandedGroups().length) renderFrames();
    renderEdges();
  } else if (drag.type === "resize") {
    drag.ann.w = Math.max(120, Math.round(drag.w + (e.clientX - drag.sx) / view.k));
    drag.ann.h = Math.max(50, Math.round(drag.h + (e.clientY - drag.sy) / view.k));
    const div = annLayer.querySelector(`[data-ann="${CSS.escape(drag.ann.id)}"]`);
    div.style.width = `${drag.ann.w}px`; div.style.height = `${drag.ann.h}px`;
  } else if (drag.type === "connect") {
    drag.moved = true;
    drag.cur = toWorld(e.clientX, e.clientY);
    const over = document.elementFromPoint(e.clientX, e.clientY)?.closest?.(".port");
    nodesLayer.querySelectorAll(".port.target").forEach((p) => p.classList.remove("target", "ok"));
    drag.bad = false;
    if (over && (over.dataset.member || over.closest(".node").dataset.id) !== drag.node) {
      const ok = !over.classList.contains("dim") && over.dataset.dir !== drag.dir;
      over.classList.add("target", ok ? "ok" : "x");
      drag.bad = !ok;
      if (ok) {
        const n = nodeById(over.dataset.member || over.closest(".node").dataset.id);
        drag.cur = portPos(n, over.dataset.dir, +over.dataset.port);
      }
    }
    renderEdges();
  } else if (drag.type === "select") {
    const r = wrap.getBoundingClientRect();
    const x0 = Math.min(drag.sx, e.clientX), y0 = Math.min(drag.sy, e.clientY);
    const x1 = Math.max(drag.sx, e.clientX), y1 = Math.max(drag.sy, e.clientY);
    Object.assign(selRect.style, { left: `${x0 - r.left}px`, top: `${y0 - r.top}px`, width: `${x1 - x0}px`, height: `${y1 - y0}px` });
    selRect.classList.remove("hidden");
    const a = toWorld(x0, y0), b = toWorld(x1, y1);
    store.selection = new Set(drag.base);
    const hidden = hiddenNodes();
    for (const n of store.wf.nodes) if (!hidden.has(n.id) && n.x + NODE_W > a.x && n.x < b.x && n.y + NODE_H > a.y && n.y < b.y) store.selection.add(n.id);
    for (const g of collapsedGroups()) if (g.x + NODE_W > a.x && g.x < b.x && g.y + groupHeight(g) > a.y && g.y < b.y) store.selection.add(g.id);
    syncSelection();
  }
}

function onMouseUp(e) {
  if (!drag) return;
  const d = drag;
  drag = null;
  wrap.classList.remove("panning");
  if (d.type === "pan" && !d.moved && d.clearOnClick) {
    if (store.selection.size || store.selectedEdge !== null) { store.selection.clear(); store.selectedEdge = null; syncSelection(); }
  } else if (d.type === "move") {
    nodesLayer.querySelectorAll(".dragging").forEach((n) => n.classList.remove("dragging"));
    annLayer.querySelectorAll(".dragging").forEach((n) => n.classList.remove("dragging"));
    if (d.moved) commit("layout");
    else if (d.items.length === 1 && nodeById(d.items[0].id)) {
      // Clic simple sur un nœud : rien de plus (sélection déjà faite).
    }
  } else if (d.type === "resize") {
    commit("annotation");
  } else if (d.type === "select") {
    selRect.classList.add("hidden");
  } else if (d.type === "connect") {
    clearTargets();
    const over = document.elementFromPoint(e.clientX, e.clientY)?.closest?.(".port");
    let done = false;
    if (over) {
      const nid = over.dataset.member || over.closest(".node").dataset.id;
      const odir = over.dataset.dir, oport = +over.dataset.port;
      if (odir !== d.dir && nid !== d.node && over.dataset.kind === d.kind) {
        done = d.dir === "out" ? connect(d.node, d.port, nid, oport) : connect(nid, oport, d.node, d.port);
      }
    } else if (d.dir === "out" && !d.moved) {
      // Simple clic sur une sortie : afficher la table / le modèle.
      select([d.node]);
      emit("show-port", { node: d.node, port: d.port });
    } else if (d.moved && !d.detached && !e.target.closest?.(".node")) {
      quickAdd(e.clientX, e.clientY, { node: d.node, port: d.port, kind: d.kind, dir: d.dir });
    }
    if (d.detached && !done) commit("structure");
    renderEdges();
  }
}

function onWheel(e) {
  e.preventDefault();
  const r = wrap.getBoundingClientRect();
  if (e.ctrlKey || e.metaKey || Math.abs(e.deltaY) >= 40 && !e.shiftKey && e.deltaMode === 0 && Number.isInteger(e.deltaY)) {
    zoomBy(Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.0018)), e.clientX - r.left, e.clientY - r.top);
  } else {
    // Pavé tactile : défilement à deux doigts = déplacement.
    view.x -= e.deltaX; view.y -= e.deltaY;
    applyView();
  }
}

function onDblClick(e) {
  const groupDiv = e.target.closest(".group-node");
  if (groupDiv) { toggleGroup(groupDiv.dataset.id, false); return; }
  const frameHead = e.target.closest("[data-framehead]");
  if (frameHead) { toggleGroup(frameHead.dataset.framehead, true); return; }
  const nodeDiv = e.target.closest(".node");
  const annDiv = e.target.closest(".annotation");
  if (nodeDiv) { emit("configure", nodeDiv.dataset.id); return; }
  if (annDiv) { editAnnotation(annById(annDiv.dataset.ann)); return; }
  if (!e.target.closest(".port, [data-edge]")) quickAdd(e.clientX, e.clientY);
}

function onContextMenu(e) {
  e.preventDefault();
  const groupDiv = e.target.closest(".group-node") || e.target.closest("[data-framehead]");
  if (groupDiv) {
    const gid = groupDiv.dataset.id || groupDiv.dataset.framehead;
    const g = groupById(gid);
    if (g.collapsed && !store.selection.has(gid)) select([gid]);
    emit("group-menu", { id: gid, x: e.clientX, y: e.clientY });
    return;
  }
  const nodeDiv = e.target.closest(".node");
  const annDiv = e.target.closest(".annotation");
  const edgeHit = e.target.closest("[data-edge]");
  if (nodeDiv) {
    const id = nodeDiv.dataset.id;
    if (!store.selection.has(id)) select([id]);
    emit("node-menu", { id, x: e.clientX, y: e.clientY });
  } else if (annDiv) {
    const a = annById(annDiv.dataset.ann);
    select([a.id]);
    contextMenu(e.clientX, e.clientY, [
      { label: "Modifier le texte", icon: "i-note", action: () => editAnnotation(a) },
      { header: "Couleur" },
      ...Object.keys(ANN_COLORS).map((c) => ({ label: c[0].toUpperCase() + c.slice(1), action: () => { a.color = c; commit("annotation"); renderAnnotations(); } })),
      "-",
      { label: "Supprimer", icon: "i-trash", danger: true, key: "Suppr", action: deleteSelection },
    ]);
  } else if (edgeHit) {
    store.selection.clear();
    store.selectedEdge = +edgeHit.dataset.edge;
    syncSelection();
    contextMenu(e.clientX, e.clientY, [{ label: "Supprimer la connexion", icon: "i-trash", danger: true, key: "Suppr", action: deleteSelection }]);
  } else {
    const at = toWorld(e.clientX, e.clientY);
    contextMenu(e.clientX, e.clientY, [
      { label: "Ajouter un nœud…", icon: "i-plus", key: "Double-clic", action: () => quickAdd(e.clientX, e.clientY) },
      { label: "Ajouter une annotation", icon: "i-note", key: "A", action: () => addAnnotation({ x: at.x + 140, y: at.y + 50 }) },
      { label: "Coller", icon: "i-copy", key: "Ctrl+V", action: () => paste() },
      "-",
      { label: "Tout sélectionner", key: "Ctrl+A", action: () => select([...store.wf.nodes.map((n) => n.id), ...(store.wf.annotations || []).map((a) => a.id)]) },
      { label: "Ajuster à l'écran", icon: "i-fit", key: "F", action: fitView },
    ]);
  }
}

// Dépôt d'un nœud depuis le dépôt (glisser-déposer HTML5).
function onDrop(e) {
  const comp = e.dataTransfer.getData("application/x-kataml-component");
  if (comp) { e.preventDefault(); emit("insert-component", { id: comp, at: toWorld(e.clientX, e.clientY) }); return; }
  const type = e.dataTransfer.getData("application/x-kataml-node");
  if (!type) return;
  e.preventDefault();
  const at = toWorld(e.clientX, e.clientY);
  // Déposé sur un nœud existant : on relie automatiquement.
  const target = document.elementFromPoint(e.clientX, e.clientY)?.closest(".node");
  addNode(type, { x: at.x, y: at.y }, target ? target.dataset.id : null);
}

export function initEditor() {
  wrap = document.getElementById("canvas-wrap");
  world = document.getElementById("world");
  edgesSvg = document.getElementById("edges");
  nodesLayer = document.getElementById("nodes");
  annLayer = document.getElementById("annotations");
  selRect = document.getElementById("selection-rect");
  wrap.addEventListener("mousedown", onMouseDown);
  window.addEventListener("mousemove", onMouseMove);
  window.addEventListener("mouseup", onMouseUp);
  wrap.addEventListener("wheel", onWheel, { passive: false });
  wrap.addEventListener("dblclick", onDblClick);
  wrap.addEventListener("contextmenu", onContextMenu);
  wrap.addEventListener("dragover", (e) => {
    const t = e.dataTransfer.types;
    if (t.includes("application/x-kataml-node") || t.includes("application/x-kataml-component")) { e.preventDefault(); e.dataTransfer.dropEffect = "copy"; }
  });
  wrap.addEventListener("drop", onDrop);
  window.addEventListener("keydown", (e) => { if (e.code === "Space" && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName)) { spaceDown = true; } });
  window.addEventListener("keyup", (e) => { if (e.code === "Space") spaceDown = false; });
  applyView();
  on("states", refreshAllNodes);
}
