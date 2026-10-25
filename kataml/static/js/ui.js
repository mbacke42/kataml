// Utilitaires d'interface : création d'éléments, icônes, toasts, modales, menus.

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "style" && typeof v === "object") Object.assign(node.style, v);
    else if (k === "dataset") Object.assign(node.dataset, v);
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else if (k === "html") node.innerHTML = v;
    else if (v === true) node.setAttribute(k, "");
    else node.setAttribute(k, v);
  }
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}

const SVGNS = "http://www.w3.org/2000/svg";
export function svg(tag, attrs = {}, ...children) {
  const node = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === undefined || v === null) continue;
    if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}

export function icon(id, cls = "i") {
  const s = document.createElementNS(SVGNS, "svg");
  s.setAttribute("class", cls);
  const u = document.createElementNS(SVGNS, "use");
  u.setAttribute("href", `#${id}`);
  s.append(u);
  return s;
}

export function debounce(fn, ms) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

const LOCALE = (() => {
  try { return (globalThis.KATAML_LANG || localStorage.getItem("kataml.lang")) === "en" ? "en-US" : "fr-FR"; }
  catch { return globalThis.KATAML_LANG === "en" ? "en-US" : "fr-FR"; }
})();
export function fmt(v, digits = 4) {
  if (v === null || v === undefined) return "";
  if (typeof v === "number") {
    if (!Number.isFinite(v)) return String(v);
    if (Number.isInteger(v)) return v.toLocaleString(LOCALE);
    const a = Math.abs(v);
    if (a !== 0 && (a < 1e-3 || a >= 1e7)) return v.toExponential(3);
    return v.toLocaleString(LOCALE, { maximumFractionDigits: digits });
  }
  return String(v);
}

export function dtypeClass(dtype = "") {
  if (/int|float|uint|number/.test(dtype)) return "num";
  if (/bool/.test(dtype)) return "bool";
  if (/object|str|category/.test(dtype)) return "str";
  return "";
}

// Famille visuelle d'un nœud : couleur et icône.
export const FAMILY = {
  data: { color: "var(--c-io)", icon: "c-io" },
  io: { color: "var(--c-io)", icon: "c-io" },
  manip: { color: "var(--c-manip)", icon: "c-manip" },
  view: { color: "var(--c-view)", icon: "c-view" },
  learner: { color: "var(--c-learner)", icon: "c-learner" },
  regressor: { color: "var(--c-regressor)", icon: "c-regressor" },
  cluster: { color: "var(--c-cluster)", icon: "c-cluster" },
  transformer: { color: "var(--c-transformer)", icon: "c-transformer" },
  apply: { color: "var(--c-apply)", icon: "c-apply" },
  score: { color: "var(--c-score)", icon: "c-score" },
  tune: { color: "var(--c-tune)", icon: "c-tune" },
  compose: { color: "var(--c-compose)", icon: "c-compose" },
  explain: { color: "var(--c-explain)", icon: "c-explain" },
  group: { color: "var(--c-group)", icon: "c-group" },
  report: { color: "var(--c-report)", icon: "c-report" },
  ext: { color: "var(--c-ext)", icon: "c-ext" },
};

export function familyOf(spec) {
  if (!spec) return FAMILY.manip;
  if (spec.type.startsWith("io.")) return FAMILY.io;
  if (spec.type.startsWith("manip.")) return FAMILY.manip;
  if (spec.type.startsWith("sk.regressor.")) return FAMILY.regressor;
  return FAMILY[spec.color] || (spec.extension ? FAMILY.ext : FAMILY.manip);
}

// ---------- Toasts ----------
export function toast(msg, kind = "") {
  const box = document.getElementById("toasts");
  const t = el("div", { class: `toast ${kind}` },
    kind === "ok" ? icon("i-check") : kind === "err" ? icon("i-warn") : null, msg);
  box.append(t);
  setTimeout(() => { t.style.transition = "opacity .25s"; t.style.opacity = "0"; }, kind === "err" ? 5200 : 2600);
  setTimeout(() => t.remove(), kind === "err" ? 5500 : 2900);
}

// ---------- Modales ----------
let modalClose = null;
export function openModal({ title, body, footer = [], wide = false, onClose }) {
  const back = document.getElementById("modal-backdrop");
  const modal = document.getElementById("modal");
  modal.className = `modal${wide ? " wide" : ""}`;
  modal.replaceChildren(
    el("div", { class: "modal-head" }, el("h3", {}, title),
      el("button", { class: "btn ghost icon", title: "Fermer (Échap)", onclick: () => closeModal() }, icon("i-x"))),
    el("div", { class: "modal-body" }, body),
    footer.length ? el("div", { class: "modal-foot" }, footer) : null,
  );
  back.classList.remove("hidden");
  modalClose = onClose || null;
  back.onmousedown = (e) => { if (e.target === back) closeModal(); };
  const first = modal.querySelector("input, select, textarea");
  if (first) setTimeout(() => first.focus(), 30);
  return modal;
}
export function closeModal() {
  document.getElementById("modal-backdrop").classList.add("hidden");
  if (modalClose) { const f = modalClose; modalClose = null; f(); }
}
export function modalOpen() {
  return !document.getElementById("modal-backdrop").classList.contains("hidden");
}

export function prompt(title, label, value = "", okLabel = "Valider") {
  return new Promise((resolve) => {
    const input = el("input", { class: "field-input", value });
    let done = false;
    const ok = () => { done = true; closeModal(); resolve(input.value.trim() || null); };
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") ok(); });
    openModal({
      title,
      body: el("div", { class: "field" }, el("label", {}, label), input),
      footer: [el("button", { class: "btn", onclick: () => closeModal() }, "Annuler"),
               el("button", { class: "btn primary", onclick: ok }, okLabel)],
      onClose: () => { if (!done) resolve(null); },
    });
    setTimeout(() => input.select(), 40);
  });
}

export function confirmBox(title, text, okLabel = "Confirmer", danger = false) {
  return new Promise((resolve) => {
    let done = false;
    openModal({
      title, body: el("p", { style: { margin: 0 } }, text),
      footer: [el("button", { class: "btn", onclick: () => closeModal() }, "Annuler"),
               el("button", { class: `btn ${danger ? "danger" : "primary"}`, onclick: () => { done = true; closeModal(); resolve(true); } }, okLabel)],
      onClose: () => { if (!done) resolve(false); },
    });
  });
}

// ---------- Menu contextuel ----------
export function contextMenu(x, y, items) {
  const menu = document.getElementById("ctxmenu");
  menu.replaceChildren(...items.map((it) => {
    if (it === "-") return el("hr");
    if (it.header) return el("div", { class: "mh" }, it.header);
    return el("button", {
      class: it.danger ? "danger" : "", disabled: it.disabled,
      onclick: () => { hideMenu(); it.action(); },
    }, it.icon ? icon(it.icon) : el("span", { style: { width: "16px" } }), it.label, it.key ? el("span", { class: "k" }, it.key) : null);
  }));
  menu.classList.remove("hidden");
  const r = menu.getBoundingClientRect();
  menu.style.left = `${Math.min(x, innerWidth - r.width - 8)}px`;
  menu.style.top = `${Math.min(y, innerHeight - r.height - 8)}px`;
}
export function hideMenu() { document.getElementById("ctxmenu")?.classList.add("hidden"); }
document.addEventListener("mousedown", (e) => {
  if (!e.target.closest?.("#ctxmenu")) hideMenu();
});

export function download(filename, content, type = "text/plain") {
  const blob = content instanceof Blob ? content : new Blob([content], { type });
  const a = el("a", { href: URL.createObjectURL(blob), download: filename });
  document.body.append(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
}

// Coloration syntaxique Python minimale (export de code).
export function highlightPython(code) {
  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const re = /(#[^\n]*)|("""[\s\S]*?"""|'''[\s\S]*?'''|f?"(?:[^"\\\n]|\\.)*"|f?'(?:[^'\\\n]|\\.)*')|\b(import|from|as|def|return|for|in|if|else|elif|not|and|or|None|True|False|print|with|lambda|while|class|try|except)\b|\b(\d+\.?\d*(?:e-?\d+)?)\b/g;
  let out = "", last = 0, m;
  while ((m = re.exec(code))) {
    out += esc(code.slice(last, m.index));
    const cls = m[1] ? "com" : m[2] ? "str" : m[3] ? "kw" : "num";
    out += `<span class="${cls}">${esc(m[0])}</span>`;
    last = re.lastIndex;
  }
  return out + esc(code.slice(last));
}

// ---------- Recherche de nœuds ----------
export function norm(s) {
  return (s || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}
const splitCamel = (s) => (s || "").replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2");

// Score de pertinence d'un nœud pour une requête (0 = aucun résultat).
export function searchScore(sp, query) {
  const q = norm(query).trim();
  if (!q) return 1;
  const name = norm(sp.name);
  if (name === q) return 100;
  if (name.startsWith(q)) return 80;
  const words = norm(`${splitCamel(sp.name)} ${sp.category} ${sp.family || ""} ${sp.keywords || ""}`).split(/[^a-z0-9]+/).filter(Boolean);
  const tokens = q.split(/\s+/);
  if (tokens.every((t) => words.some((w) => w.startsWith(t)))) return name.includes(q) ? 60 : 40;
  if (name.includes(q)) return 30;
  return 0;
}
