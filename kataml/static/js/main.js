// Point d'entrée : chargement du catalogue, barre d'outils, exécution, raccourcis.

import { el, icon, toast, openModal, closeModal, modalOpen, prompt, confirmBox, contextMenu, download, debounce, highlightPython } from "./ui.js";
import { api } from "./api.js";
import {
  store, on, emit, spec, nodeById, groupById, commit, resetHistory, undo, redo, emptyWorkflow,
  ancestors, descendants, topoOrder, missingConfig, wireWorkflow,
} from "./state.js";
import {
  initEditor, render, addNode, addAnnotation, deleteSelection, copySelection, paste,
  select, fitView, zoomBy, zoomReset, viewCenter, autoLayout, createGroup, toggleGroup, ungroup,
  renameGroup, groupAsComponent, insertComponent, pipelinePlan, createPipeline, canContractPipeline, contractPipeline, refreshAllNodes,
} from "./editor.js";
import { initRepository, loadComponents, renderRepository } from "./repository.js";
import { blocksDialog, convertScriptToBlock, reportDialog, setupExtras } from "./extras.js";
import { startTranslation, t, lang } from "./i18n.js";
import { initInspector, uploadFile } from "./inspector.js";
import { projectDialog, convertScripts, setProjectHooks, addReader } from "./project.js";
import { initOutputs } from "./outputs.js";
import { initTheme, themeDialog, toggleMode } from "./theme.js";

const LS = {
  get(k, d = null) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* stockage indisponible */ } },
};

// ---------- Thème ----------
initTheme(() => emit("states"));

// ---------- États ----------
async function refreshStatus() {
  try {
    const res = await api.status(wireWorkflow());
    for (const [id, s] of Object.entries(res.states)) {
      const cur = store.states[id]?.state;
      if (cur === "running" || cur === "queued") continue;
      store.states[id] = s;
    }
    for (const id of Object.keys(store.states)) if (!nodeById(id)) delete store.states[id];
    emit("states");
  } catch (e) {
    console.warn(e);
  }
  await syncColumns();
}
const refreshStatusSoon = debounce(refreshStatus, 200);

// ---------- Colonnes disponibles ----------
// Met à jour les colonnes connues de chaque nœud (formulaires de l'inspecteur) et retire des
// paramètres les colonnes qui n'existent plus en entrée, par exemple après un changement de
// jeu de données. Les colonnes encore inconnues (nœud amont non exécuté) ne sont pas touchées.
async function syncColumns({ duringRun = false } = {}) {
  if (store.running && !duringRun) return;
  let columns;
  try { ({ columns } = await api.columnsAll(wireWorkflow())); } catch { return; }
  if (store.running && !duringRun) return;
  const changed = [], removed = new Set();
  for (const [id, ports] of Object.entries(columns)) {
    const node = nodeById(id);
    if (!node) continue;
    if (JSON.stringify(store.columns[id] || null) !== JSON.stringify(ports)) changed.push(id);
    store.columns[id] = ports;
    for (const p of spec(node.type)?.params || []) {
      if (p.type !== "column" && p.type !== "columns") continue;
      const cols = ports?.[p.port || 0];
      const cur = node.params[p.name];
      if (!cols || cur === undefined || cur === null || cur === "") continue;
      const names = new Set(cols.map((c) => c.name));
      if (p.type === "column" && !names.has(cur)) {
        delete node.params[p.name];
        removed.add(cur);
      } else if (p.type === "columns" && Array.isArray(cur) && cur.some((c) => !names.has(c))) {
        cur.filter((c) => !names.has(c)).forEach((c) => removed.add(c));
        node.params[p.name] = cur.filter((c) => names.has(c));
      }
      if (removed.size && !changed.includes(id)) changed.push(id);
    }
  }
  if (removed.size) {
    commit("param");
    refreshAllNodes();
    const list = [...removed].slice(0, 6).join(", ") + (removed.size > 6 ? "…" : "");
    toast(t("Colonnes absentes de la table d'entrée retirées de la configuration : {list} (Ctrl+Z pour annuler)", { list }));
  }
  if (changed.length) emit("columns", changed);
}

// ---------- Exécution ----------
let stopRequested = false;

function setRunning(r) {
  store.running = r;
  document.querySelector('[data-action="stop"]').classList.toggle("hidden", !r);
  document.querySelector('[data-action="run-all"]').disabled = r;
}

// Nœuds désignés par une liste d'identifiants (les groupes sont remplacés par leurs membres).
function expandIds(ids) {
  return [...new Set(ids.flatMap((id) => groupById(id)?.nodes || [id]))].filter((id) => nodeById(id));
}
const selectedNodes = () => expandIds([...store.selection]);

async function execute(ids, { all = false } = {}) {
  if (store.running) { toast("Une exécution est déjà en cours."); return; }
  ids = expandIds(ids);
  if (!ids.length) return;
  const set = new Set();
  for (const id of ids) { set.add(id); for (const a of ancestors(id)) set.add(a); }
  await refreshStatus();
  let order = topoOrder([...set]).filter((id) => store.states[id]?.state !== "executed");
  if (all) {
    // Exécution globale : on ignore les nœuds incomplets et leurs descendants.
    const skip = new Set();
    for (const id of order) if (missingConfig(nodeById(id)).length) { skip.add(id); for (const d of descendants(id)) skip.add(d); }
    order = order.filter((id) => !skip.has(id));
    if (skip.size) toast(`${skip.size} nœud(s) non configuré(s) ignoré(s).`);
  }
  if (!order.length) { toast("Tout est déjà exécuté.", "ok"); return; }
  setRunning(true);
  stopRequested = false;
  for (const id of order) store.states[id] = { state: "queued" };
  emit("states");
  const failed = new Set();
  let errors = 0, reconfigure = 0;
  const t0 = performance.now();
  for (const id of order) {
    if (stopRequested) break;
    const blocked = [...ancestors(id)].some((a) => failed.has(a));
    if (blocked) { failed.add(id); store.states[id] = { state: "idle" }; continue; }
    // Les nœuds déjà exécutés ont pu révéler de nouvelles colonnes : on retire les colonnes
    // disparues avant d'exécuter celui-ci, et on l'écarte s'il n'est plus configuré.
    await syncColumns({ duringRun: true });
    if (missingConfig(nodeById(id)).length) { failed.add(id); reconfigure++; store.states[id] = { state: "idle" }; continue; }
    store.states[id] = { state: "running" };
    emit("states");
    try {
      const res = await api.execute(wireWorkflow(), id);
      Object.assign(store.states, res.states);
      if (res.cancelled) { stopRequested = true; break; }
      if (!res.ok) {
        failed.add(id);
        errors++;
        if (!res.states[id]) store.states[id] = { state: "error", message: res.error };
        if (!all || errors === 1) toast(`${spec(nodeById(id).type).name} : ${res.error}`, "err");
      }
    } catch (e) {
      failed.add(id);
      store.states[id] = { state: "error", message: e.message };
      toast(e.message, "err");
    }
    emit("states");
  }
  for (const id of order) if (["queued", "running"].includes(store.states[id]?.state)) store.states[id] = { state: "idle" };
  setRunning(false);
  await refreshStatus();
  if (reconfigure) toast(t("{n} nœud(s) à reconfigurer après le retrait de colonnes absentes : non exécuté(s).", { n: reconfigure }), "err");
  if (!errors && !stopRequested) {
    const s = (performance.now() - t0) / 1000;
    toast(`${order.length} nœud(s) exécuté(s) en ${s.toFixed(1)} s`, "ok");
  } else if (stopRequested) toast("Exécution arrêtée.");
}

async function resetNodes(ids) {
  ids = expandIds(ids);
  const set = new Set();
  for (const id of ids) { set.add(id); for (const d of descendants(id)) set.add(d); }
  await api.reset([...set]);
  await refreshStatus();
}

// ---------- Menu contextuel des nœuds ----------
on("node-menu", ({ id, x, y }) => {
  const node = nodeById(id);
  const sp = spec(node.type);
  const st = store.states[id];
  const executed = st?.state === "executed";
  const ids = [...store.selection].filter((s) => nodeById(s));
  const items = [
    { label: ids.length > 1 ? `Exécuter (${ids.length})` : "Exécuter", icon: "i-play", key: "F7", action: () => execute(ids) },
    { label: "Exécuter jusqu'en aval", icon: "i-play-all", action: () => execute([id, ...descendants(id)]) },
    { label: "Réinitialiser", icon: "i-reset", key: "F8", disabled: !executed && st?.state !== "error", action: () => resetNodes(ids) },
    { label: "Configurer", icon: "i-gear", key: "Double-clic", action: () => emit("configure", id) },
    "-",
  ];
  if (executed) {
    if (sp.has_view && st.has_view) items.push({ label: "Afficher la vue", icon: "i-chart", action: () => emit("show-port", { node: id, port: "view" }) });
    sp.outputs.forEach((o, i) => items.push({ label: `Sortie : ${o.name}`, icon: o.kind === "data" ? "i-table" : "i-box", action: () => emit("show-port", { node: id, port: i }) }));
    sp.outputs.forEach((o, i) => items.push({ label: `Télécharger : ${o.name}`, icon: "i-download", action: () => { location.href = api.downloadUrl(id, i, (node.label || sp.name).replace(/\s+/g, "_")); } }));
    items.push("-");
  }
  if (ids.length > 1) {
    items.push({ label: "Grouper en composant", icon: "c-group", key: "Ctrl+G", action: groupSelection });
    if (pipelinePlan(ids)) items.push({ label: "Créer un Pipeline", icon: "c-compose", action: () => newPipeline(ids) });
    items.push({ label: "Organiser la sélection", icon: "i-layout", key: "L", action: () => autoLayout(ids) });
    items.push("-");
  }
  if (canContractPipeline(id)) {
    items.push({ label: "Contracter le Pipeline", icon: "c-compose", action: () => contractPipeline(id) }, "-");
  }
  if (node.type === "manip.python") {
    items.push({ label: "Convertir en bloc réutilisable…", icon: "c-ext", action: () => convertScriptToBlock(node) }, "-");
  }
  items.push(
    { label: "Copier", icon: "i-copy", key: "Ctrl+C", action: copySelection },
    { label: "Dupliquer", key: "Ctrl+D", action: () => { copySelection(); paste(30); } },
    { label: "Supprimer", icon: "i-trash", key: "Suppr", danger: true, action: deleteSelection },
  );
  contextMenu(x, y, items);
});

on("group-menu", ({ id, x, y }) => {
  const g = groupById(id);
  contextMenu(x, y, [
    { label: g.collapsed ? "Déplier" : "Réduire", icon: "c-group", key: "Double-clic", action: () => toggleGroup(id) },
    { label: "Exécuter le composant", icon: "i-play", key: "F7", action: () => execute(g.nodes) },
    { label: "Réinitialiser", icon: "i-reset", action: () => resetNodes(g.nodes) },
    "-",
    { label: "Renommer…", action: async () => { const n = await prompt("Renommer le composant", "Nom", g.name); if (n) renameGroup(id, n); } },
    { label: "Enregistrer comme composant réutilisable…", icon: "i-save", action: () => saveComponent(id) },
    { label: "Dissocier", action: () => ungroup(id) },
    "-",
    { label: "Supprimer", icon: "i-trash", key: "Suppr", danger: true, action: () => { select([id]); deleteSelection(); } },
  ]);
});

function newPipeline(ids) {
  if (createPipeline(ids)) toast("Pipeline créé et contracté : double-clic pour voir ses étapes", "ok");
}

async function groupSelection() {
  const ids = [...store.selection].filter((id) => nodeById(id));
  if (ids.length < 2) { toast("Sélectionnez au moins deux nœuds."); return; }
  const name = await prompt("Grouper en composant", "Nom du composant", "Composant", "Grouper");
  if (name) createGroup(ids, name);
}

async function saveComponent(id) {
  const g = groupById(id);
  const name = await prompt("Composant réutilisable", "Nom (enregistré dans workspace/components)", g.name, "Enregistrer");
  if (!name) return;
  try {
    await api.saveComponent({ ...groupAsComponent(id), name });
    await loadComponents();
    toast(`Composant « ${name} » ajouté au dépôt (Mes composants)`, "ok");
  } catch (e) { toast(e.message, "err"); }
}

on("save-component", (id) => saveComponent(id));
on("insert-component", async ({ id, at }) => {
  try {
    const { component } = await api.loadComponent(id);
    insertComponent(component, at);
  } catch (e) { toast(e.message, "err"); }
});
on("delete-component", async ({ id, name }) => {
  if (!(await confirmBox("Supprimer le composant", `Supprimer « ${name} » du dépôt ? Les workflows qui l'utilisent ne sont pas modifiés.`, "Supprimer", true))) return;
  try { await api.deleteComponent(id); await loadComponents(); } catch (e) { toast(e.message, "err"); }
});

on("execute", (ids) => execute(ids));
on("reset", (ids) => resetNodes(ids));
on("refresh-status", refreshStatusSoon);

// ---------- Persistance ----------
const autosave = debounce(() => LS.set("kataml.autosave", { wf: store.wf, savedName: store.savedName || null }), 400);
function updateDirty() {
  document.getElementById("wf-dirty").classList.toggle("on", store.dirty);
  document.title = `${store.dirty ? "• " : ""}${store.wf.name === "Sans titre" ? t("Sans titre") : store.wf.name} — KataML`;
}
on("changed", (kind) => {
  autosave();
  updateDirty();
  if (kind !== "layout" && kind !== "annotation" && kind !== "label") refreshStatusSoon();
});

function loadWorkflow(wf, savedName = null, fit = true) {
  const base = emptyWorkflow();
  store.wf = { ...base, ...wf, nodes: wf.nodes || [], edges: wf.edges || [], annotations: wf.annotations || [], groups: wf.groups || [] };
  // Nœuds dont le type n'existe pas (autre version de scikit-learn).
  const unknown = store.wf.nodes.filter((n) => !spec(n.type));
  if (unknown.length) toast(`${unknown.length} nœud(s) de type inconnu (version de scikit-learn différente ?)`, "err");
  store.savedName = savedName;
  store.states = {};
  store.columns = {};
  store.selection = new Set();
  store.dirty = false;
  document.getElementById("wf-name").value = store.wf.name || "Sans titre";
  resetHistory();
  render();
  if (fit) setTimeout(fitView, 30);
  emit("selection");
  updateDirty();
  autosave();
  refreshStatus();
}
on("loaded", () => { render(); document.getElementById("wf-name").value = store.wf.name; refreshStatusSoon(); });

async function newWorkflow() {
  if (store.dirty && store.wf.nodes.length && !(await confirmBox("Nouveau workflow", "Les modifications non enregistrées seront perdues.", "Continuer", true))) return;
  loadWorkflow(emptyWorkflow());
}

async function saveWorkflow(forceName = false) {
  let name = store.savedName;
  if (!name || forceName) {
    name = await prompt("Enregistrer le workflow", "Nom (enregistré dans workspace/workflows)", store.wf.name || "workflow", "Enregistrer");
    if (!name) return;
  }
  try {
    const res = await api.saveWorkflow(name, store.wf);
    store.savedName = res.name;
    store.dirty = false;
    updateDirty();
    autosave();
    toast(`Enregistré : ${res.name}.json`, "ok");
  } catch (e) { toast(e.message, "err"); }
}

async function openDialog(examplesFirst = false) {
  let data;
  try { data = await api.workflows(); } catch (e) { toast(e.message, "err"); return; }
  const confirmLoss = async () => !(store.dirty && store.wf.nodes.length) || confirmBox("Ouvrir un workflow", "Les modifications non enregistrées seront perdues.", "Continuer", true);
  const pick = async (q, savedName) => {
    closeModal();
    if (!(await confirmLoss())) return;
    try {
      const res = await api.loadWorkflow(q);
      loadWorkflow(res.workflow, savedName);
      toast(`« ${res.workflow.name || savedName} » ouvert`, "ok");
    } catch (e) { toast(e.message, "err"); }
  };
  const examples = el("div", { class: "wf-list" }, el("h4", {}, "Exemples"),
    data.examples.map((ex) => el("button", { class: "wf-item", onclick: () => pick({ example: ex.id }, null) },
      el("div", { class: "wi" }, icon("i-book")), el("div", {}, el("div", { class: "wt" }, ex.name), el("div", { class: "wd" }, ex.description)))));
  const mine = el("div", { class: "wf-list" }, el("h4", {}, "Mes workflows (workspace/workflows)"),
    data.workflows.length ? data.workflows.map((w) => el("button", { class: "wf-item", onclick: () => pick({ name: w }, w) },
      el("div", { class: "wi" }, icon("i-folder")), el("div", {}, el("div", { class: "wt" }, w))))
      : el("div", { class: "wd", style: { color: "var(--muted)", padding: "6px 2px" } }, "Aucun workflow enregistré pour l'instant."));
  const importBtn = el("button", { class: "btn", onclick: () => {
    const input = document.getElementById("file-input");
    input.accept = ".json,application/json";
    input.value = "";
    input.onchange = async () => {
      const f = input.files[0];
      if (!f) return;
      try {
        const wf = JSON.parse(await f.text());
        closeModal();
        if (!(await confirmLoss())) return;
        loadWorkflow(wf, null);
      } catch { toast("Fichier JSON invalide.", "err"); }
    };
    input.click();
  } }, icon("i-upload"), "Importer un fichier .json");
  const scriptBtn = el("button", { class: "btn", title: "Reconstruit le schéma à partir d'un script pandas / scikit-learn. Sélectionnez aussi les modules qu'il importe (constantes, fonctions).", onclick: () => {
    const input = document.getElementById("file-input");
    input.accept = ".py,text/x-python";
    input.multiple = true;
    input.value = "";
    input.onchange = async () => {
      const files = [...input.files];
      input.multiple = false;
      if (!files.length) return;
      closeModal();
      await importScripts(files);
    };
    input.click();
  } }, icon("i-upload"), "Importer un script Python (.py)");
  openModal({
    title: "Ouvrir un workflow",
    body: el("div", { style: { display: "grid", gap: "8px" } }, ...(examplesFirst ? [examples, mine] : [mine, examples])),
    footer: [importBtn, scriptBtn, el("span", { style: { flex: 1 } }),
      el("button", { class: "btn", onclick: () => download(`${store.wf.name || "workflow"}.json`, JSON.stringify(store.wf, null, 1), "application/json") }, icon("i-download"), "Exporter le workflow courant (.json)")],
  });
}

async function exportPython() {
  if (!store.wf.nodes.length) { toast("Le workflow est vide."); return; }
  const name = (store.wf.name || "workflow").replace(/[^\w-]+/g, "_");
  const wf = { ...wireWorkflow(), annotations: store.wf.annotations || [], name: store.wf.name };
  let code;
  try { code = (await api.exportCode(wf, name, "py")).code; } catch (e) { toast(e.message, "err"); return; }
  const pre = el("pre", { class: "code", html: highlightPython(code) });
  const saveNotebook = async () => {
    try {
      const nb = (await api.exportCode(wf, name, "ipynb")).code;
      download(`${name}.ipynb`, nb, "application/x-ipynb+json");
    } catch (e) { toast(e.message, "err"); }
  };
  openModal({
    title: "Exporter en Python", wide: true,
    body: el("div", {}, el("p", { style: { margin: "0 0 10px", color: "var(--text-2)" } },
      "Le workflow est reproduit avec pandas et scikit-learn uniquement. Le notebook Jupyter contient une cellule par nœud ; les annotations deviennent du texte."), pre),
    footer: [
      el("button", { class: "btn", onclick: async () => { try { await navigator.clipboard.writeText(code); toast("Copié", "ok"); } catch { toast("Copie impossible", "err"); } } }, icon("i-copy"), "Copier"),
      el("button", { class: "btn", onclick: saveNotebook }, icon("i-book"), `Notebook ${name}.ipynb`),
      el("button", { class: "btn primary", onclick: () => download(`${name}.py`, code, "text/x-python") }, icon("i-download"), `Script ${name}.py`),
    ],
  });
}

function helpDialog() {
  const k = (keys, label) => el("div", {}, el("span", {}, label), el("span", {}, keys.map((x, i) => [i ? " " : "", el("kbd", {}, x)])));
  openModal({
    title: "Prise en main de KataML", wide: true,
    body: el("div", {},
      el("p", { style: { marginTop: 0 } }, "Dans KataML, un workflow est un graphe de nœuds reliés par des ports. Chaque nœud se configure, s'exécute, puis expose ses sorties. Tout le calcul repose sur pandas et scikit-learn ; chaque workflow s'exporte en script Python."),
      el("div", { class: "legend-row" },
        el("span", {}, el("span", { class: "traffic" }, el("i", { style: { background: "var(--err)", opacity: 1 } }), el("i"), el("i")), "À configurer ou en erreur"),
        el("span", {}, el("span", { class: "traffic" }, el("i"), el("i", { style: { background: "var(--warn)", opacity: 1 } }), el("i")), "Configuré, prêt à exécuter"),
        el("span", {}, el("span", { class: "traffic" }, el("i"), el("i"), el("i", { style: { background: "var(--ok)", opacity: 1 } })), "Exécuté")),
      el("div", { class: "legend-row" },
        el("span", {}, el("span", { style: { display: "inline-block", borderTop: "6px solid transparent", borderBottom: "6px solid transparent", borderLeft: "9px solid var(--port-data)" } }), "Port table (DataFrame)"),
        el("span", {}, el("span", { style: { display: "inline-block", width: "9px", height: "9px", background: "var(--port-model)", borderRadius: "2px" } }), "Port modèle (estimateur ajusté)")),
      el("h4", {}, "Démarche type"),
      el("ol", {},
        el("li", {}, "Lire les données (Lecteur CSV ou Jeu de données scikit-learn)."),
        el("li", {}, "Explorer (Statistiques, Nuage de points, Corrélations)."),
        el("li", {}, "Partitionner en apprentissage / test."),
        el("li", {}, "Prétraiter (StandardScaler, OneHotEncoder…) et appliquer le même transformeur au test."),
        el("li", {}, "Entraîner un modèle, le connecter à un Prédicteur avec la table de test."),
        el("li", {}, "Pour une évaluation sans fuite, regrouper prétraitements et modèle dans un nœud Pipeline (clic droit sur la sélection → « Créer un Pipeline »)."),
        el("li", {}, "Évaluer (Évaluation classification / régression, Courbe ROC, Validation croisée, Comparer des modèles)."),
        el("li", {}, "Comprendre le modèle (Frontière de décision, Visualiser l'arbre, Dépendance partielle, Importance).")),
      el("h4", {}, "Raccourcis"),
      el("div", { class: "help-grid" },
        k(["F7"], "Exécuter la sélection"), k(["Maj", "F7"], "Tout exécuter"),
        k(["F8"], "Réinitialiser la sélection"), k(["Suppr"], "Supprimer"),
        k(["Ctrl", "C"], "Copier"), k(["Ctrl", "V"], "Coller"),
        k(["Ctrl", "D"], "Dupliquer"), k(["Ctrl", "A"], "Tout sélectionner"),
        k(["Ctrl", "Z"], "Annuler"), k(["Ctrl", "Y"], "Rétablir"),
        k(["Ctrl", "S"], "Enregistrer"), k(["F"], "Ajuster à l'écran"),
        k(["A"], "Nouvelle annotation"), k(["Double-clic"], "Chercher et ajouter un nœud"),
        k(["L"], "Organiser automatiquement"), k(["Ctrl", "G"], "Grouper en composant"),
        k(["Ctrl", "P"], "Générer un rapport"), k(["Mes blocs"], "Créer vos propres blocs"),
        k(["Molette"], "Zoomer"), k(["Glisser le fond"], "Se déplacer"),
        k(["Maj", "glisser"], "Sélection rectangulaire"), k(["Alt", "glisser"], "Déplacer sans grille")),
      el("p", {}, el("a", { href: lang === "en" ? "https://fredbl.gitlab.io/kataml/en/" : "https://fredbl.gitlab.io/kataml/", target: "_blank", rel: "noopener" },
        icon("i-book"), " ", t("Documentation complète et tutoriels"), " ", icon("i-external"))),
      el("h4", {}, "Rapports, blocs personnalisés, ligne de commande"),
      el("p", {}, "« Rapport » produit un fichier HTML autonome (imprimable en PDF) avec le schéma du workflow, les vues des nœuds choisis et les blocs « Texte du rapport ». « Mes blocs » permet d'écrire vos propres nœuds en Python, ou de convertir un nœud Script Python en bloc réutilisable. Sans interface : kataml run workflow.json --rapport rapport.html."),
      el("h4", {}, "Données"),
      el("p", {}, "Les fichiers importés sont copiés dans workspace/data ; les workflows enregistrés vont dans workspace/workflows et les exports dans workspace/exports. Vous pouvez aussi glisser un fichier CSV directement sur le canevas.")),
  });
}

async function quitApp() {
  const msg = store.dirty && store.wf.nodes.length
    ? "Le workflow courant reste sauvegardé dans ce navigateur, mais n'est pas enregistré dans l'espace de travail. Arrêter quand même ?"
    : "Le serveur KataML va s'arrêter. Vous pourrez fermer cet onglet.";
  if (!(await confirmBox("Quitter KataML", msg, "Quitter", true))) return;
  try { await api.shutdown(); } catch { /* le serveur est peut-être déjà arrêté */ }
  document.body.replaceChildren(el("div", { class: "insp-empty", style: { margin: "18vh auto", maxWidth: "460px", textAlign: "center" } },
    el("img", { src: "img/logo.svg", width: 56, height: 56, alt: "" }),
    el("h3", { style: { fontSize: "18px", margin: "14px 0 6px" } }, "KataML est arrêté"),
    el("p", {}, "Vous pouvez fermer cet onglet. Relancez l'application pour reprendre : le dernier workflow sera restauré.")));
}

// ---------- Barre d'outils ----------
const ACTIONS = {
  project: () => projectDialog(),
  "new": newWorkflow,
  "open": () => openDialog(false),
  "open-examples": () => openDialog(true),
  "save": () => saveWorkflow(false),
  "undo": () => undo(),
  "redo": () => redo(),
  "annotate": () => addAnnotation(),
  "export-py": exportPython,
  "layout": () => autoLayout(selectedNodes()),
  "report": () => reportDialog(execute),
  "blocks": () => blocksDialog(),
  "reset-all": async () => { await api.reset(null); await refreshStatus(); toast("Workflow réinitialisé"); },
  "run-all": () => execute(store.wf.nodes.map((n) => n.id), { all: true }),
  "stop": async () => {
    stopRequested = true;
    try {
      const r = await api.cancel();
      toast(r.ok ? "Calcul interrompu ; le moteur redémarre…" : "Arrêt demandé.");
    } catch (e) { toast(e.message, "err"); }
  },
  "help": helpDialog,
  "theme": toggleMode,
  "appearance": themeDialog,
  "quit": quitApp,
  "lang": () => {
    try { localStorage.setItem("kataml.lang", lang === "en" ? "fr" : "en"); } catch { /* */ }
    location.reload();
  },
  "zoom-in": () => zoomBy(1.2),
  "zoom-out": () => zoomBy(1 / 1.2),
  "zoom-reset": zoomReset,
  "fit": fitView,
  "toggle-bottom": () => document.getElementById("bottom").classList.toggle("collapsed"),
};
document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-action]");
  if (b && ACTIONS[b.dataset.action]) ACTIONS[b.dataset.action]();
});

document.getElementById("wf-name").addEventListener("input", debounce((e) => {
  store.wf.name = e.target.value.trim() || "Sans titre";
  commit("label");
}, 300));

// ---------- Clavier ----------
document.addEventListener("keydown", (e) => {
  const tag = document.activeElement?.tagName;
  const typing = /INPUT|TEXTAREA|SELECT/.test(tag) || document.activeElement?.isContentEditable;
  const mod = e.ctrlKey || e.metaKey;
  if (e.key === "Escape" && modalOpen()) { closeModal(); return; }
  if (modalOpen()) return;
  if (mod && e.key.toLowerCase() === "s") { e.preventDefault(); saveWorkflow(e.shiftKey); return; }
  if (e.key === "F1") { e.preventDefault(); helpDialog(); return; }
  if (e.key === "F7") { e.preventDefault(); if (e.shiftKey) ACTIONS["run-all"](); else execute(selectedNodes()); return; }
  if (e.key === "F8") { e.preventDefault(); resetNodes(selectedNodes()); return; }
  if (typing) return;
  if (mod && e.key.toLowerCase() === "z" && !e.shiftKey) { e.preventDefault(); undo(); }
  else if (mod && (e.key.toLowerCase() === "y" || (e.key.toLowerCase() === "z" && e.shiftKey))) { e.preventDefault(); redo(); }
  else if (mod && e.key.toLowerCase() === "c") { if (copySelection()) toast("Copié"); }
  else if (mod && e.key.toLowerCase() === "v") { paste(); }
  else if (mod && e.key.toLowerCase() === "d") { e.preventDefault(); if (copySelection()) paste(30); }
  else if (mod && e.key.toLowerCase() === "a") { e.preventDefault(); select([...store.wf.nodes.map((n) => n.id), ...(store.wf.annotations || []).map((a) => a.id)]); }
  else if (e.key === "Delete" || e.key === "Backspace") { e.preventDefault(); deleteSelection(); }
  else if (e.key === "Escape") { select([]); }
  else if (e.key.toLowerCase() === "f" && !mod) { fitView(); }
  else if (e.key.toLowerCase() === "a" && !mod) { addAnnotation(); }
  else if (e.key.toLowerCase() === "l" && !mod) { autoLayout(selectedNodes()); }
  else if (mod && e.key.toLowerCase() === "g") { e.preventDefault(); groupSelection(); }
  else if (mod && e.key.toLowerCase() === "p") { e.preventDefault(); reportDialog(execute); }
  else if (e.key === "+" || e.key === "=") { zoomBy(1.2); }
  else if (e.key === "-") { zoomBy(1 / 1.2); }
});

// ---------- Panneaux redimensionnables ----------
function initSplitters() {
  const root = document.documentElement;
  const sizes = LS.get("kataml.layout", {});
  for (const [k, v] of Object.entries(sizes)) root.style.setProperty(k, `${v}px`);
  document.querySelectorAll(".splitter").forEach((sp) => {
    sp.addEventListener("mousedown", (e) => {
      e.preventDefault();
      sp.classList.add("dragging");
      const kind = sp.dataset.split;
      const start = { x: e.clientX, y: e.clientY };
      const repo = document.getElementById("repo").offsetWidth;
      const insp = document.getElementById("inspector").offsetWidth;
      const bottom = document.getElementById("bottom").offsetHeight;
      document.getElementById("bottom").classList.remove("collapsed");
      const move = (ev) => {
        if (kind === "repo") sizes["--repo-w"] = Math.max(200, Math.min(520, repo + ev.clientX - start.x));
        if (kind === "inspector") sizes["--insp-w"] = Math.max(280, Math.min(720, insp - (ev.clientX - start.x)));
        if (kind === "bottom") sizes["--bottom-h"] = Math.max(120, Math.min(innerHeight - 200, bottom - (ev.clientY - start.y)));
        for (const [k, v] of Object.entries(sizes)) root.style.setProperty(k, `${v}px`);
      };
      const up = () => {
        sp.classList.remove("dragging");
        window.removeEventListener("mousemove", move);
        window.removeEventListener("mouseup", up);
        LS.set("kataml.layout", sizes);
      };
      window.addEventListener("mousemove", move);
      window.addEventListener("mouseup", up);
    });
  });
}

// Import de scripts Python : ajoutés à la bibliothèque (workspace/scripts), puis convertis
// en schéma par le serveur (le code n'est jamais exécuté).
async function importScripts(files) { await convertScripts({ files }); }
setProjectHooks({
  loadWorkflow: (wf) => loadWorkflow(wf, null),
  confirmLoss: async () => !(store.dirty && store.wf.nodes.length)
    || confirmBox("Ouvrir un workflow", "Les modifications non enregistrées seront perdues.", "Continuer", true),
});

// Lecteur adapté à l'extension du fichier déposé.
// Fichiers déposés sur le canevas : import + Lecteur CSV, Lecteur Parquet / Excel ou import de script.
function initFileDrop() {
  const wrap = document.getElementById("canvas-wrap");
  wrap.addEventListener("dragover", (e) => { if (e.dataTransfer.types.includes("Files")) { e.preventDefault(); e.dataTransfer.dropEffect = "copy"; } });
  wrap.addEventListener("drop", async (e) => {
    if (!e.dataTransfer.files?.length) return;
    e.preventDefault();
    const r = wrap.getBoundingClientRect();
    let offset = 0;
    const dropped = [...e.dataTransfer.files];   // la liste n'est plus lisible après un await
    const scripts = dropped.filter((f) => f.name.toLowerCase().endsWith(".py"));
    if (scripts.length) await importScripts(scripts);
    for (const f of dropped) {
      if (f.name.toLowerCase().endsWith(".py")) continue;
      if (f.name.endsWith(".json")) {
        try { loadWorkflow(JSON.parse(await f.text()), null); } catch { toast("JSON invalide", "err"); }
        continue;
      }
      try {
        const name = await uploadFile(f);
        const c = viewCenter();
        const node = addReader(name, { x: c.x + (e.clientX - r.left - r.width / 2) + offset, y: c.y + (e.clientY - r.top - r.height / 2) + offset });
        if (node) select([node.id]);
        offset += 80;
      } catch (err) { toast(err.message, "err"); }
    }
  });
}

window.addEventListener("beforeunload", (e) => {
  if (store.running) { e.preventDefault(); e.returnValue = ""; }
});

// Catalogue des nœuds (rechargé quand des blocs personnalisés changent).
async function loadCatalog() {
  const cat = await api.catalog();
  store.meta = cat;
  store.catalog.clear();
  for (const n of cat.nodes) store.catalog.set(n.type, n);
}
export async function reloadCatalog() {
  await loadCatalog();
  renderRepository();
  refreshAllNodes();
  emit("selection");
  await refreshStatus();
}
on("catalog-changed", reloadCatalog);
store.reloadCatalog = reloadCatalog;

// ---------- Mise à jour disponible ----------
// Vérification discrète côté serveur (une requête GitLab par jour, sans donnée
// personnelle, silencieuse hors ligne). Un bandeau refermable s'affiche si une
// version plus récente existe ; « Ignorer » le masque jusqu'à la suivante.
async function checkForUpdate() {
  let info;
  try { info = await api.update(); } catch { return; }
  if (!info || !info.available || !info.latest) return;
  if (LS.get("kataml.updateDismissed") === info.latest) return;
  const bar = el("div", { class: "update-banner", role: "status" },
    icon("i-external"),
    el("span", {}, t("KataML {latest} est disponible (vous avez {current}).",
      { latest: info.latest, current: info.current })),
    el("a", { href: info.url, target: "_blank", rel: "noopener" }, t("Notes de version")),
    el("button", {
      class: "btn ghost sm", title: t("Ne plus signaler cette version"),
      onclick: () => { LS.set("kataml.updateDismissed", info.latest); bar.remove(); },
    }, t("Ignorer")));
  document.body.append(bar);
}

// ---------- Démarrage ----------
async function boot() {
  startTranslation();
  const langBtn = document.querySelector('[data-action="lang"]');
  if (langBtn) langBtn.textContent = lang === "en" ? "FR" : "EN";
  initEditor();
  initSplitters();
  try {
    await loadCatalog();
  } catch (e) {
    toast(`Impossible de charger le catalogue : ${e.message}`, "err");
    return;
  }
  setupExtras();
  const broken = (store.meta.extensions || []).filter((x) => x.error);
  if (broken.length) toast(`Extension(s) en erreur : ${broken.map((x) => x.name).join(", ")} — voir « Mes blocs »`, "err");
  initRepository();
  initInspector();
  initOutputs();
  initFileDrop();
  const saved = LS.get("kataml.autosave");
  if (saved?.wf?.nodes) {
    loadWorkflow(saved.wf, saved.savedName, false);
    store.dirty = !!saved.savedName ? false : saved.wf.nodes.length > 0;
    updateDirty();
    setTimeout(fitView, 30);
  } else {
    loadWorkflow(emptyWorkflow(), null, false);
  }
  checkForUpdate();
}
boot();
