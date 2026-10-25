// Données et scripts : fichiers de workspace/data (CSV, Parquet, Excel, SQLite) et
// bibliothèque de scripts Python (workspace/scripts), convertibles en schéma.
import { el, icon, toast, openModal, closeModal, confirmBox, prompt } from "./ui.js";
import { api } from "./api.js";
import { commit } from "./state.js";
import { render, addNode, viewCenter } from "./editor.js";
import { uploadFile } from "./inspector.js";

// Extension -> [libellé, type de nœud, paramètre du fichier]
const DATA_KINDS = [
  [/\.(csv|tsv|txt|data)$/i, "CSV", "io.csv_reader", "path"],
  [/\.(parquet|pq|feather)$/i, "Parquet", "io.table_reader", "path"],
  [/\.(xlsx|xlsm|xls)$/i, "Excel", "io.table_reader", "path"],
  [/\.(db|sqlite|sqlite3|db3)$/i, "SQLite", "io.sql_reader", "source"],
];
export const DATA_ACCEPT = ".csv,.tsv,.txt,.data,.parquet,.pq,.feather,.xlsx,.xlsm,.xls,.db,.sqlite,.sqlite3,.db3";
export function dataKind(name) { return DATA_KINDS.find(([re]) => re.test(name)) || null; }

// Dossiers ignorés à l'import d'un projet (environnements, caches, dépôts).
const IGNORED_DIRS = new Set([".venv", "venv", "env", ".env", ".git", "__pycache__", "node_modules", "site-packages",
  ".ipynb_checkpoints", ".ruff_cache", ".mypy_cache", ".pytest_cache", "dist", "build", ".idea", ".vscode", ".tox"]);
// Fichiers de données repérés dans un dossier importé : envoyés seulement quand un schéma les utilise.
const pending = new Map();
let hooks = { loadWorkflow: () => {}, confirmLoss: async () => true };
export function setProjectHooks(h) { hooks = { ...hooks, ...h }; }

const TEMPLATE = `"""Mon script : décrivez ici ce qu'il fait.

Écrivez du pandas / scikit-learn comme d'habitude, puis « Créer le schéma »
pour obtenir le workflow correspondant.
"""
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

CIBLE = "ma_colonne_cible"

df = pd.read_csv("mes_donnees.csv")
df = df.dropna()
X = df.drop(columns=CIBLE)
y = df[CIBLE]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, stratify=y, random_state=0)
modele = RandomForestClassifier(n_estimators=200, random_state=0).fit(X_train, y_train)
print(accuracy_score(y_test, modele.predict(X_test)))
`;

const size = (n) => n > 1e6 ? `${(n / 1e6).toFixed(1)} Mo` : `${Math.max(1, Math.round(n / 1024))} Ko`;

function pickFiles(accept, multiple = true) {
  return new Promise((resolve) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = accept;
    input.multiple = multiple;
    input.onchange = () => resolve([...input.files]);
    input.click();
  });
}

// ---------- Lecteurs ----------
export function addReader(name, at = null) {
  const k = dataKind(name);
  const node = addNode(k ? k[2] : "io.csv_reader", at || viewCenter());
  if (!node) return null;
  node.params[k ? k[3] : "path"] = name;
  node.label = name;
  commit("param");
  render();
  return node;
}

async function uploadData(files) {
  const names = [];
  for (const f of files) {
    try { names.push(await uploadFile(f)); pending.delete(f.name); } catch (e) { toast(`${f.name} : ${e.message}`, "err"); }
  }
  return names;
}

// ---------- Scripts ----------
async function saveScripts(files) {
  const saved = [];
  const seen = new Set();
  for (const f of files) {
    if (seen.has(f.name)) continue;          // même nom dans deux sous-dossiers : le premier est gardé
    seen.add(f.name);
    try { saved.push((await api.saveScript(f.name, await f.text())).file); } catch (e) { toast(`${f.name} : ${e.message}`, "err"); }
  }
  return saved;
}

// Convertit des scripts en schéma. ``files`` : fichiers à ajouter d'abord à la bibliothèque ;
// ``names`` : scripts déjà dans la bibliothèque. Les autres scripts servent de modules s'ils sont importés.
export async function convertScripts({ files = [], names = [] } = {}) {
  try {
    const saved = await saveScripts(files);
    const res = await api.importScript({ scripts: [...new Set([...names, ...saved])] });
    if (!(await hooks.confirmLoss())) return;
    hooks.loadWorkflow(res.workflow);
    const n = res.workflow.nodes.length;
    toast(res.notes.length ? `${n} nœuds reconstruits — ${res.notes.length} point(s) à vérifier (voir la note sur le canevas).`
      : `${n} nœuds reconstruits à partir du script.`, res.notes.length ? "" : "ok");
    await resolveMissing(res.missing_data || []);
  } catch (e) { toast(e.message, "err"); }
}

// Fichiers lus par le schéma mais absents de workspace/data.
async function resolveMissing(missing) {
  const base = (p) => p.replace(/\\/g, "/").split("/").pop();
  const fromFolder = missing.map((p) => pending.get(base(p))).filter(Boolean);
  if (fromFolder.length) {
    toast(`Import de ${fromFolder.length} fichier(s) de données du dossier…`);
    await uploadData(fromFolder);
  }
  const rest = missing.filter((p) => !pending.has(base(p)) && !fromFolder.some((f) => f.name === base(p)));
  if (!rest.length) return;
  openModal({
    title: "Données à importer",
    body: el("div", {},
      el("p", { style: { marginTop: 0 } }, "Le schéma lit ces fichiers, qui ne sont pas encore dans workspace/data :"),
      el("ul", {}, rest.map((p) => el("li", {}, el("code", {}, base(p))))),
      el("p", { class: "wd", style: { color: "var(--text-2)" } },
        "Importez-les maintenant (même nom de fichier), ou plus tard en les déposant sur le canevas ou depuis la fenêtre « Données »."),
    ),
    footer: [el("button", { class: "btn", onclick: () => closeModal() }, "Plus tard"),
      el("button", { class: "btn primary", onclick: async () => {
        const files = await pickFiles(DATA_ACCEPT);
        closeModal();
        if (files.length) await uploadData(files);
      } }, icon("i-upload"), "Importer ces fichiers")],
  });
}

// Import d'un dossier de projet : scripts dans la bibliothèque, données gardées en attente.
export async function importFolder() {
  const input = document.createElement("input");
  input.type = "file";
  input.webkitdirectory = true;
  input.multiple = true;
  input.onchange = async () => {
    const usable = [...input.files].filter((f) =>
      !(f.webkitRelativePath || f.name).split("/").slice(0, -1).some((d) => IGNORED_DIRS.has(d)));
    const scripts = usable.filter((f) => f.name.endsWith(".py") && f.size > 0 && f.size < 2e6
      && !/^(test_.*|.*_test|conftest|setup|__init__)\.py$/.test(f.name));
    const data = usable.filter((f) => dataKind(f.name));
    data.forEach((f) => pending.set(f.name, f));
    const saved = await saveScripts(scripts);
    toast(`${saved.length} script(s) ajouté(s) à la bibliothèque, ${data.length} fichier(s) de données repéré(s).`, "ok");
    projectDialog({ highlight: saved });
  };
  input.click();
}

async function editScript(file, opts) {
  let source = "";
  try { source = (await api.readScript(file)).source; } catch (e) { toast(e.message, "err"); return; }
  const ta = el("textarea", { class: "code-editor", spellcheck: "false" });
  ta.value = source;
  const status = el("div", { class: "wd", style: { minHeight: "18px", marginTop: "8px" } });
  const save = async () => {
    try { await api.saveScript(file, ta.value); status.replaceChildren(el("span", { style: { color: "var(--ok)" } }, "Enregistré.")); return true; }
    catch (e) { status.replaceChildren(el("div", { class: "insp-error" }, e.message)); return false; }
  };
  ta.addEventListener("keydown", (e) => {
    if (e.key === "Tab") { e.preventDefault(); ta.setRangeText("    ", ta.selectionStart, ta.selectionEnd, "end"); }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); save(); }
    e.stopPropagation();
  });
  openModal({
    title: `Script ${file}`, wide: true,
    body: el("div", {}, ta, status),
    footer: [el("button", { class: "btn", onclick: () => projectDialog(opts) }, "Retour à la liste"),
      el("span", { style: { flex: 1 } }),
      el("button", { class: "btn", onclick: save }, icon("i-save"), "Enregistrer (Ctrl+S)"),
      el("button", { class: "btn primary", onclick: async () => { if (await save()) { closeModal(); convertScripts({ names: [file] }); } } },
        "Enregistrer et créer le schéma")],
  });
}

async function newScript(opts) {
  const name = await prompt("Nouveau script", "Nom du fichier", "mon_script.py", "Créer");
  if (!name) { projectDialog(opts); return; }
  try {
    const r = await api.saveScript(name.endsWith(".py") ? name : `${name}.py`, TEMPLATE);
    editScript(r.file, opts);
  } catch (e) { toast(e.message, "err"); projectDialog(opts); }
}

// ---------- Fenêtre « Données et scripts » ----------
export async function projectDialog(opts = {}) {
  let files, lib;
  try { [files, lib] = await Promise.all([api.files(), api.scripts()]); } catch (e) { toast(e.message, "err"); return; }
  const present = new Set(files.files.map((f) => f.name));
  const chosen = new Set((opts.chosen || []).filter((n) => lib.scripts.some((s) => s.name === n)));
  const fresh = new Set(opts.highlight || []);       // scripts que l'on vient d'ajouter
  const again = () => projectDialog({ ...opts, chosen: [...chosen] });

  const kindTag = (name) => el("span", { class: "proj-kind" }, dataKind(name)?.[1] || "Fichier");
  const dataRows = files.files.map((f) => el("div", { class: "blk" }, kindTag(f.name),
    el("div", { style: { minWidth: 0 } }, el("div", { class: "wt" }, f.name), el("div", { class: "wd" }, size(f.size))),
    el("div", { class: "acts" },
      dataKind(f.name) ? el("button", { class: "btn sm", title: "Crée le lecteur adapté sur le canevas", onclick: () => { closeModal(); addReader(f.name); } },
        icon("i-plus"), "Au canevas") : null,
      el("button", { class: "btn sm icon", title: "Retirer de workspace/data", onclick: async () => {
        if (await confirmBox("Retirer le fichier", `Supprimer ${f.name} de workspace/data ? Les nœuds qui le lisent ne trouveront plus le fichier.`, "Supprimer", true)) {
          try { await api.deleteData(f.name); } catch (e) { toast(e.message, "err"); }
        }
        again();
      } }, icon("i-trash")))));
  const waiting = [...pending.values()].filter((f) => !present.has(f.name)).map((f) => el("div", { class: "blk proj-pending" }, kindTag(f.name),
    el("div", { style: { minWidth: 0 } }, el("div", { class: "wt" }, f.name), el("div", { class: "wd" }, `${size(f.size)} · repéré dans le dossier, pas encore importé`)),
    el("div", { class: "acts" }, el("button", { class: "btn sm", onclick: async () => { await uploadData([f]); again(); } }, icon("i-upload"), "Importer"))));

  const scriptRows = lib.scripts.map((s) => {
    const box = el("input", { type: "checkbox", checked: chosen.has(s.name), title: "Script à convertir en schéma",
      onchange: (e) => { e.target.checked ? chosen.add(s.name) : chosen.delete(s.name); convert.disabled = !chosen.size; convert.lastChild.textContent = label(); } });
    return el("div", { class: fresh.has(s.name) ? "blk proj-new" : "blk" }, box,
      el("div", { style: { minWidth: 0 } }, el("div", { class: "wt" }, s.name),
        el("div", { class: "wd" }, `${size(s.size)}${s.main ? " · script principal (if __name__ == \"__main__\")" : ""}`)),
      el("div", { class: "acts" },
        el("button", { class: "btn sm", onclick: () => editScript(s.name, { ...opts, chosen: [...chosen] }) }, "Voir / modifier"),
        el("button", { class: "btn sm icon", title: "Retirer de la bibliothèque", onclick: async () => {
          if (await confirmBox("Retirer le script", `Supprimer ${s.name} de la bibliothèque de scripts ?`, "Supprimer", true)) {
            try { await api.deleteScript(s.name); chosen.delete(s.name); } catch (e) { toast(e.message, "err"); }
          }
          again();
        } }, icon("i-trash"))));
  });
  const label = () => chosen.size ? `Créer le schéma (${chosen.size} script${chosen.size > 1 ? "s" : ""})` : "Créer le schéma";
  const convert = el("button", { class: "btn primary", disabled: !chosen.size,
    onclick: () => { closeModal(); convertScripts({ names: [...chosen] }); } }, el("span", {}, label()));

  const body = el("div", { class: "proj" },
    el("p", { style: { marginTop: 0, color: "var(--text-2)" } },
      "Rassemblez ici les données et les scripts d'un projet. Déposez des fichiers dans cette fenêtre, ou importez tout un dossier : les scripts rejoignent la bibliothèque, les données utiles sont importées au moment de créer le schéma."),
    el("div", { class: "proj-cols" },
      el("section", { class: "wf-list" },
        el("div", { class: "proj-head" }, el("h4", {}, "Données (workspace/data)"),
          el("button", { class: "btn sm", onclick: async () => { const f = await pickFiles(DATA_ACCEPT); if (f.length) { await uploadData(f); again(); } } },
            icon("i-upload"), "Importer")),
        el("p", { class: "wd", style: { color: "var(--muted)", margin: "0 0 8px" } }, "CSV, Parquet, Excel ou base SQLite. Pour PostgreSQL ou MySQL, ajoutez un nœud « Lecteur SQL »."),
        el("div", { class: "blk-list" }, dataRows.length || waiting.length ? [...waiting, ...dataRows]
          : el("div", { class: "wd", style: { color: "var(--muted)" } }, "Aucun fichier pour l'instant."))),
      el("section", { class: "wf-list" },
        el("div", { class: "proj-head" }, el("h4", {}, "Scripts (workspace/scripts)"),
          el("div", { class: "tools" },
            el("button", { class: "btn sm", onclick: async () => { const f = await pickFiles(".py,text/x-python"); if (f.length) { (await saveScripts(f)).forEach((n) => chosen.add(n)); again(); } } },
              icon("i-upload"), "Ajouter"),
            el("button", { class: "btn sm", onclick: () => newScript({ ...opts, chosen: [...chosen] }) }, icon("i-plus"), "Nouveau"))),
        el("p", { class: "wd", style: { color: "var(--muted)", margin: "0 0 8px" } },
          "Cochez le ou les scripts à convertir. Les autres servent de modules s'ils sont importés (constantes, fonctions)."),
        el("div", { class: "blk-list" }, scriptRows.length ? scriptRows
          : el("div", { class: "wd", style: { color: "var(--muted)" } }, "Aucun script. Ajoutez vos fichiers .py ou partez d'un modèle avec « Nouveau ».")))));
  body.addEventListener("dragover", (e) => { if (e.dataTransfer.types.includes("Files")) { e.preventDefault(); body.classList.add("drop"); } });
  body.addEventListener("dragleave", () => body.classList.remove("drop"));
  body.addEventListener("drop", async (e) => {
    e.preventDefault();
    e.stopPropagation();
    body.classList.remove("drop");
    const all = [...e.dataTransfer.files];
    (await saveScripts(all.filter((f) => f.name.endsWith(".py")))).forEach((n) => chosen.add(n));
    await uploadData(all.filter((f) => !f.name.endsWith(".py")));
    again();
  });
  openModal({
    title: "Données et scripts", wide: true, body,
    footer: [el("button", { class: "btn", onclick: importFolder, title: "Choisir le dossier d'un projet : scripts .py et fichiers de données (les dossiers .venv, .git… sont ignorés)" },
      icon("i-folder"), "Importer un dossier de projet"), el("span", { style: { flex: 1 } }), convert],
  });
}
