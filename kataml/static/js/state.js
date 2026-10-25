// État central de l'application : catalogue, workflow, états d'exécution,
// sélection et historique (annuler / rétablir).

import { t } from "./i18n.js";

const listeners = new Map();

export const store = {
  catalog: new Map(),          // type -> spécification
  meta: {},
  wf: emptyWorkflow(),
  states: {},                  // id -> {state, message, outputs, has_view, …}
  columns: {},                 // id -> colonnes connues par port d'entrée
  selection: new Set(),        // ids de nœuds / annotations
  selectedEdge: null,
  dirty: false,
  running: false,
};

export function emptyWorkflow() {
  return { version: 1, name: t("Sans titre"), nodes: [], edges: [], annotations: [], groups: [] };
}

export function on(evt, fn) {
  if (!listeners.has(evt)) listeners.set(evt, new Set());
  listeners.get(evt).add(fn);
}
export function emit(evt, payload) {
  for (const fn of listeners.get(evt) || []) fn(payload);
}

export const spec = (type) => store.catalog.get(type);
export const nodeById = (id) => store.wf.nodes.find((n) => n.id === id);
export const annById = (id) => (store.wf.annotations || []).find((a) => a.id === id);
export const groupById = (id) => (store.wf.groups || []).find((g) => g.id === id);
// Groupe réduit qui contient le nœud (le nœud est alors masqué sur le canevas).
export const collapsedGroupOf = (nodeId) => (store.wf.groups || []).find((g) => g.collapsed && g.nodes.includes(nodeId));
export const groupOf = (nodeId) => (store.wf.groups || []).find((g) => g.nodes.includes(nodeId));

export function newId(prefix = "n") {
  const used = new Set([...store.wf.nodes.map((n) => n.id), ...(store.wf.annotations || []).map((a) => a.id),
    ...(store.wf.groups || []).map((g) => g.id)]);
  let i = 1;
  while (used.has(`${prefix}${i}`)) i++;
  return `${prefix}${i}`;
}

// ---------- Historique ----------
const undoStack = [];
const redoStack = [];
let lastSnapshot = null;

const snapshot = () => JSON.stringify(store.wf);

export function resetHistory() {
  undoStack.length = 0;
  redoStack.length = 0;
  lastSnapshot = snapshot();
}

// À appeler après chaque modification du workflow.
export function commit(kind = "structure") {
  const snap = snapshot();
  if (snap === lastSnapshot) return;
  if (lastSnapshot !== null) undoStack.push(lastSnapshot);
  if (undoStack.length > 150) undoStack.shift();
  redoStack.length = 0;
  lastSnapshot = snap;
  store.dirty = true;
  emit("changed", kind);
}

function restore(snap) {
  store.wf = JSON.parse(snap);
  lastSnapshot = snap;
  store.selection = new Set([...store.selection].filter((id) => nodeById(id) || annById(id) || groupById(id)));
  store.dirty = true;
  emit("loaded", { keepView: true });
  emit("changed", "structure");
}
export function undo() {
  if (!undoStack.length) return false;
  redoStack.push(snapshot());
  restore(undoStack.pop());
  return true;
}
export function redo() {
  if (!redoStack.length) return false;
  undoStack.push(snapshot());
  restore(redoStack.pop());
  return true;
}

// ---------- Graphe ----------
export function incoming(id) {
  return store.wf.edges.filter((e) => e.to === id);
}
export function outgoing(id) {
  return store.wf.edges.filter((e) => e.from === id);
}

export function ancestors(id, acc = new Set()) {
  for (const e of incoming(id)) {
    if (!acc.has(e.from)) { acc.add(e.from); ancestors(e.from, acc); }
  }
  return acc;
}
export function descendants(id, acc = new Set()) {
  for (const e of outgoing(id)) {
    if (!acc.has(e.to)) { acc.add(e.to); descendants(e.to, acc); }
  }
  return acc;
}

// Ordre topologique (Kahn), départage par position horizontale puis verticale.
export function topoOrder(ids = null) {
  const set = new Set(ids || store.wf.nodes.map((n) => n.id));
  const indeg = new Map([...set].map((id) => [id, 0]));
  for (const e of store.wf.edges) if (set.has(e.from) && set.has(e.to)) indeg.set(e.to, indeg.get(e.to) + 1);
  const pos = (id) => { const n = nodeById(id); return n ? [n.x, n.y] : [0, 0]; };
  const ready = [...set].filter((id) => indeg.get(id) === 0);
  const order = [];
  while (ready.length) {
    ready.sort((a, b) => pos(a)[0] - pos(b)[0] || pos(a)[1] - pos(b)[1]);
    const id = ready.shift();
    order.push(id);
    for (const e of store.wf.edges) {
      if (e.from === id && set.has(e.to)) {
        indeg.set(e.to, indeg.get(e.to) - 1);
        if (indeg.get(e.to) === 0) ready.push(e.to);
      }
    }
  }
  return order;
}

export function wouldCycle(from, to) {
  return from === to || descendants(to).has(from);
}

// État affiché d'un nœud (feu tricolore).
export function displayState(node) {
  const s = store.states[node.id]?.state;
  if (s === "running" || s === "queued") return s;
  const sp = spec(node.type);
  if (!sp) return "unconfigured";
  if (s === "executed") return "executed";
  if (s === "error") return "error";
  return missingConfig(node).length ? "unconfigured" : "configured";
}

export function missingConfig(node) {
  const sp = spec(node.type);
  const issues = [];
  if (!sp) return ["Type de nœud inconnu"];
  sp.inputs.forEach((p, i) => {
    if ((sp.optional_inputs || []).includes(i)) return;
    if (!store.wf.edges.some((e) => e.to === node.id && e.toPort === i)) issues.push(`Entrée « ${p.name} » non connectée`);
  });
  for (const p of sp.params) {
    if (!p.required) continue;
    const v = node.params?.[p.name] ?? p.default;
    if (v === undefined || v === null || v === "" || (Array.isArray(v) && !v.length)) issues.push(`Paramètre « ${p.label} » requis`);
  }
  return issues;
}

// Workflow envoyé au serveur (sans les données d'affichage superflues).
export function wireWorkflow() {
  return {
    nodes: store.wf.nodes.map((n) => ({ id: n.id, type: n.type, params: n.params || {}, x: n.x, y: n.y, label: n.label })),
    edges: store.wf.edges,
  };
}
