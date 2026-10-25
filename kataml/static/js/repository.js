// Dépôt de nœuds : arborescence par catégorie / famille, recherche, glisser-déposer.

import { el, icon, familyOf, norm, searchScore } from "./ui.js";
import { t } from "./i18n.js";
import { api } from "./api.js";
import { store, emit } from "./state.js";
import { addNode } from "./editor.js";

let components = [];
export async function loadComponents() {
  try { components = (await api.components()).components; } catch { components = []; }
  renderRepository();
  loadComponents();
}

function componentItem(c, q) {
  return el("div", {
    class: "repo-item", draggable: "true", title: `${c.name} — ${c.nodes} nœuds\nGlissez sur le canevas ou double-cliquez. Clic droit pour supprimer.`,
    ondragstart: (e) => { e.dataTransfer.setData("application/x-kataml-component", c.id); e.dataTransfer.effectAllowed = "copy"; },
    ondblclick: () => emit("insert-component", { id: c.id }),
    oncontextmenu: (e) => { e.preventDefault(); emit("delete-component", { id: c.id, name: c.name }); },
  }, el("span", { class: "bar", style: { background: "var(--c-group)" } }), el("span", { class: "nm" }, highlight(c.name, q)),
  el("span", { class: "sub" }, `${c.nodes} nœuds`));
}

const ESSENTIALS = [
  "io.csv_reader", "io.dataset", "manip.partition", "manip.column_filter", "view.statistics", "view.scatter",
  "sk.transformer.StandardScaler", "sk.transformer.OneHotEncoder", "sk.transformer.SimpleImputer", "sk.transformer.PCA",
  "sk.classifier.LogisticRegression", "sk.classifier.DecisionTreeClassifier", "sk.classifier.RandomForestClassifier",
  "sk.classifier.KNeighborsClassifier", "sk.regressor.LinearRegression", "sk.regressor.RandomForestRegressor",
  "sk.cluster.KMeans", "compose.pipeline", "apply.predictor", "apply.transformer", "score.classification",
  "score.regression", "tune.cross_validation", "tune.compare", "explain.decision_boundary", "report.text",
];

const ESSENTIALS_LABEL = () => t("Essentiels");
const SPECIAL = () => [t("Mes composants"), t("Mes blocs"), t("Extensions")];
let viewMode = (() => { try { return localStorage.getItem("kataml.repo.mode") || "guide"; } catch { return "guide"; } })();
export function setRepoMode(mode) {
  viewMode = mode;
  try { localStorage.setItem("kataml.repo.mode", mode); } catch { /* */ }
  document.querySelectorAll("[data-repo-mode]").forEach((b) => b.classList.toggle("on", b.dataset.repoMode === mode));
  renderRepository();
}

const openState = (() => {
  try { return JSON.parse(localStorage.getItem("kataml.repo.open") || "null") || { "Essentiels": true, "Essentials": true }; }
  catch { return { "Essentiels": true, "Essentials": true }; }
})();
function saveOpen() { try { localStorage.setItem("kataml.repo.open", JSON.stringify(openState)); } catch { /* */ } }


function highlight(text, q) {
  if (!q) return text;
  const i = norm(text).indexOf(q);
  if (i < 0) return text;
  return [text.slice(0, i), el("mark", {}, text.slice(i, i + q.length)), text.slice(i + q.length)];
}

function item(sp, q = "") {
  const fam = familyOf(sp);
  const first = (sp.description || "").split("\n")[0];
  const it = el("div", {
    class: "repo-item", draggable: "true", title: `${sp.name}\n${first.slice(0, 220)}`,
    ondragstart: (e) => { e.dataTransfer.setData("application/x-kataml-node", sp.type); e.dataTransfer.effectAllowed = "copy"; },
    onclick: () => emit("describe-type", sp.type),
    ondblclick: () => {
      const sel = [...store.selection].find((id) => store.wf.nodes.some((n) => n.id === id));
      const src = sel ? store.wf.nodes.find((n) => n.id === sel) : null;
      addNode(sp.type, src ? { x: src.x + 184 / 2 + 250, y: src.y + 32 } : null, src ? src.id : null);
    },
  },
  el("span", { class: "bar", style: { background: fam.color } }),
  el("span", { class: "nm" }, highlight(sp.name, q)),
  q && sp.family ? el("span", { class: "sub" }, sp.family) : null);
  return it;
}

function details(cls, key, summaryChildren, body, forceOpen = false) {
  const d = el("details", { class: cls, open: forceOpen || !!openState[key] },
    el("summary", {}, icon("i-chevron", "i chev"), ...summaryChildren), body);
  d.addEventListener("toggle", () => { if (!forceOpen) { openState[key] = d.open; saveOpen(); } });
  return d;
}

export function renderRepository() {
  const tree = document.getElementById("repo-tree");
  const q = norm(document.getElementById("repo-search").value.trim());
  const specs = [...store.catalog.values()];
  document.getElementById("repo-count").textContent = `${specs.length}`;
  const match = (sp) => searchScore(sp, q) > 0;
  // Vue « guide » : chapitres du guide scikit-learn ; vue « API » : modules Python.
  const groupOf = (sp) => viewMode === "api" ? sp.module : sp.category;
  const famOf = (sp) => viewMode === "api" ? "" : sp.family || "";
  const order = viewMode === "api" ? [] : [...(store.meta.category_order || [])];
  const byCat = new Map(order.map((c) => [c, []]));
  if (!q) byCat.set(ESSENTIALS_LABEL(), ESSENTIALS.map((type) => store.catalog.get(type)).filter(Boolean));
  for (const sp of specs) {
    if (!match(sp)) continue;
    const g = sp.extension && viewMode === "guide" && !order.includes(sp.category) ? sp.category : groupOf(sp);
    if (!byCat.has(g)) byCat.set(g, []);
    byCat.get(g).push(sp);
  }
  if (viewMode === "api") {
    const sorted = [...byCat.entries()].filter(([k]) => k !== ESSENTIALS_LABEL()).sort((a, b) =>
      (a[0] === "kataml") - (b[0] === "kataml") || a[0].localeCompare(b[0]));
    byCat.clear();
    if (!q) byCat.set(ESSENTIALS_LABEL(), ESSENTIALS.map((type) => store.catalog.get(type)).filter(Boolean));
    sorted.forEach(([k, v]) => byCat.set(k, v));
  } else {
    const ess = byCat.get(ESSENTIALS_LABEL());
    if (ess) { byCat.delete(ESSENTIALS_LABEL()); const rest = [...byCat]; byCat.clear(); byCat.set(ESSENTIALS_LABEL(), ess); rest.forEach(([k, v]) => byCat.set(k, v)); }
  }
  for (const sp of SPECIAL()) if (!byCat.has(sp)) byCat.set(sp, []);
  const frag = [];
  let total = 0;
  for (const [cat, list] of byCat) {
    if (cat === t("Mes composants")) {
      const comps = components.filter((c) => !q || norm(c.name).includes(q));
      if (!comps.length) continue;
      frag.push(details("repo-cat", cat, [
        el("span", { class: "cat-dot", style: { background: "var(--c-group)" } }, icon("c-group", "")),
        cat, el("span", { class: "n" }, comps.length)], el("div", { class: "repo-items" }, comps.map((c) => componentItem(c, q))), !!q));
      continue;
    }
    if (!list.length) continue;
    total += cat === ESSENTIALS_LABEL() ? 0 : list.length;
    const ci = cat === ESSENTIALS_LABEL() ? { color: "var(--accent)", icon: "i-check" } : familyOf(list[0]);
    const families = new Map();
    for (const sp of list) {
      const f = cat === ESSENTIALS_LABEL() ? "" : famOf(sp);
      if (!families.has(f)) families.set(f, []);
      families.get(f).push(sp);
    }
    const body = el("div", { class: "repo-items" });
    const sortByName = (a, b) => a.name.localeCompare(b.name, "fr");
    if (families.size === 1 && families.has("")) {
      body.append(...list.map((sp) => item(sp, q)));
    } else {
      for (const [f, items] of [...families].sort((a, b) => a[0].localeCompare(b[0], "fr"))) {
        if (!f) { body.append(...items.map((sp) => item(sp, q))); continue; }
        body.append(details("repo-fam", `${cat}/${f}`, [f, el("span", { class: "n" }, items.length)],
          el("div", { class: "repo-items" }, items.sort(sortByName).map((sp) => item(sp, q))), !!q));
      }
    }
    frag.push(details("repo-cat", cat, [
      el("span", { class: "cat-dot", style: { background: ci.color } }, icon(ci.icon, "")),
      cat, el("span", { class: "n" }, list.length)], body, !!q));
  }
  tree.replaceChildren(...(frag.length ? frag : [el("div", { class: "repo-empty" }, t("Aucun nœud ne correspond."))]));
  document.getElementById("repo-foot").textContent =
    `scikit-learn ${store.meta.sklearn} · pandas ${store.meta.pandas}${q ? ` · ${total} ${t("résultat(s)")}` : ""}`;
}

export function initRepository() {
  document.querySelectorAll("[data-repo-mode]").forEach((b) => {
    b.classList.toggle("on", b.dataset.repoMode === viewMode);
    b.addEventListener("click", () => setRepoMode(b.dataset.repoMode));
  });
  const search = document.getElementById("repo-search");
  search.addEventListener("input", renderRepository);
  search.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { search.value = ""; renderRepository(); }
    if (e.key === "Enter") {
      const first = document.querySelector("#repo-tree .repo-item");
      first?.dispatchEvent(new MouseEvent("dblclick"));
    }
  });
  renderRepository();
}
