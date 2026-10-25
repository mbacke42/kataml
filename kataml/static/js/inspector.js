// Inspecteur : configuration du nœud sélectionné et description.

import { el, icon, familyOf, debounce, dtypeClass, toast } from "./ui.js";
import { api } from "./api.js";
import { store, spec, nodeById, groupById, commit, emit, on, displayState, missingConfig, wireWorkflow } from "./state.js";
import { refreshNode, renderEdges, toggleGroup, renameGroup, ungroup, groupState, select, leakyCvInputs, pipelineForCv } from "./editor.js";
import { t } from "./i18n.js";

let root;
let tab = "config";
let currentId = null;
let describeType = null;
let showAdvanced = false;
let hpFilter = "";
let files = null;

const STATE_LABEL = {
  unconfigured: "Non configuré", configured: "Configuré", executed: "Exécuté",
  error: "Erreur", running: "En cours", queued: "En attente",
};

export function initInspector() {
  root = document.getElementById("inspector");
  on("selection", () => { describeType = null; render(); });
  on("describe-type", (type) => { describeType = type; renderTypeDescription(type); });
  on("configure", (id) => { tab = "config"; render(); root.querySelector(".insp-body input, .insp-body select, .insp-body textarea")?.focus(); });
  on("columns", (ids) => { if (currentId && ids.includes(currentId) && tab === "config") render(); });
  on("states", () => {
    if (currentId) renderHeadOnly();
    else if (store.selection.size === 1 && groupById([...store.selection][0])) render();
  });
  render();
}

function selectedNode() {
  const ids = [...store.selection].filter((id) => nodeById(id));
  return ids.length === 1 ? nodeById(ids[0]) : null;
}

export function render() {
  const node = selectedNode();
  currentId = node?.id || null;
  if (!node) {
    const sel = [...store.selection];
    if (sel.length === 1 && groupById(sel[0])) return renderGroup(groupById(sel[0]));
    if (describeType) return renderTypeDescription(describeType);
    return renderEmpty();
  }
  const sp = spec(node.type);
  root.replaceChildren(head(node, sp), tabs(), el("div", { class: "insp-body" }, tab === "config" ? configForm(node, sp) : description(sp)));
  if (tab === "config") loadColumns(node, false);
}

function renderHeadOnly() {
  const node = nodeById(currentId);
  if (!node) return render();
  const old = root.querySelector(".insp-head");
  if (old) old.replaceWith(head(node, spec(node.type)));
}

function renderGroup(g) {
  const state = groupState(g);
  const name = el("input", { class: "field-input", value: g.name });
  name.addEventListener("change", () => renameGroup(g.id, name.value.trim()));
  const members = g.nodes.map(nodeById).filter(Boolean).map((n) => {
    const sp = spec(n.type);
    const fam = familyOf(sp);
    const st = displayState(n);
    return el("button", { class: "wf-item", style: { padding: "7px 10px" }, title: "Afficher et configurer ce nœud",
      onclick: () => { if (g.collapsed) toggleGroup(g.id, false); select([n.id]); } },
    el("span", { class: "cat-dot", style: { background: fam.color } }, icon(fam.icon, "")),
    el("div", { style: { flex: 1, minWidth: 0 } }, el("div", { class: "wt" }, n.label || sp?.name || n.type),
      n.label ? el("div", { class: "wd" }, sp?.name) : null),
    el("span", { class: `pill ${st}` }, STATE_LABEL[st] || st));
  });
  root.replaceChildren(
    el("div", { class: "insp-head" },
      el("div", { class: "insp-title" },
        el("div", { class: "ico", style: { background: "var(--c-group)" } }, icon("c-group", "")),
        el("div", { style: { minWidth: 0 } }, el("h3", {}, g.name), el("div", { class: "cat" }, `Composant · ${g.nodes.length} nœuds`))),
      el("div", { class: "insp-label" }, name),
      el("div", { class: "insp-state" },
        el("span", { class: `pill ${state}` }, STATE_LABEL[state] || state),
        el("div", { class: "insp-actions" },
          el("button", { class: "btn sm", onclick: () => toggleGroup(g.id) }, g.collapsed ? "Déplier" : "Réduire"),
          el("button", { class: "btn sm primary", onclick: () => emit("execute", g.nodes) }, icon("i-play"), "Exécuter")))),
    el("div", { class: "insp-body" },
      el("div", { class: "group" }, el("div", { class: "group-head" }, el("h4", {}, "Nœuds du composant")),
        el("div", { class: "wf-list" }, members)),
      el("div", { class: "group" },
        el("p", { class: "desc", style: { marginTop: 0 } }, "Les ports du composant sont les entrées et sorties de ses nœuds qui ne sont pas reliées à l'intérieur du groupe. Enregistré, il apparaît dans le dépôt (« Mes composants ») et se réutilise dans d'autres workflows."),
        el("div", { style: { display: "flex", gap: "6px", flexWrap: "wrap" } },
          el("button", { class: "btn", onclick: () => emit("save-component", g.id) }, icon("i-save"), "Enregistrer comme composant"),
          el("button", { class: "btn", onclick: () => ungroup(g.id) }, "Dissocier")))));
}

function renderEmpty() {
  const nSel = [...store.selection].filter((id) => nodeById(id)).length;
  root.replaceChildren(el("div", { class: "insp-empty" },
    el("h3", {}, nSel > 1 ? `${nSel} nœuds sélectionnés` : "Aucun nœud sélectionné"),
    el("p", {}, nSel > 1 ? "Exécutez-les avec F7, supprimez-les avec Suppr ou copiez-les avec Ctrl+C."
      : "Sélectionnez un nœud pour le configurer et lire sa documentation."),
    el("ul", {},
      el("li", {}, "Glissez un nœud du dépôt sur le canevas, ou double-cliquez sur le canevas pour en chercher un."),
      el("li", {}, "Tirez une connexion depuis une sortie ▸ vers une entrée. Relâchée dans le vide, elle propose les nœuds compatibles."),
      el("li", {}, "Les feux indiquent l'état : rouge = à configurer, orange = prêt, vert = exécuté."),
      el("li", {}, "Cliquez sur une sortie d'un nœud exécuté pour voir la table ou le modèle."),
    ),
    el("div", { class: "legend-row" },
      el("span", {}, el("span", { class: "port-glyph data desc", style: { display: "inline-block", width: 0, height: 0, borderTop: "5px solid transparent", borderBottom: "5px solid transparent", borderLeft: "8px solid var(--port-data)" } }), "Table"),
      el("span", {}, el("span", { style: { display: "inline-block", width: "8px", height: "8px", background: "var(--port-model)", borderRadius: "2px" } }), "Modèle"))));
}

function head(node, sp) {
  const fam = familyOf(sp);
  const state = displayState(node);
  const st = store.states[node.id] || {};
  const label = el("input", { class: "field-input", value: node.label || "", placeholder: "Annotation du nœud (ex. « modèle final »)" });
  label.addEventListener("input", debounce(() => { node.label = label.value; commit("label"); refreshNode(node.id); }, 250));
  const issues = state === "unconfigured" ? missingConfig(node) : [];
  return el("div", { class: "insp-head" },
    el("div", { class: "insp-title" },
      el("div", { class: "ico", style: { background: fam.color } }, icon(fam.icon, "")),
      el("div", { style: { minWidth: 0 } }, el("h3", { title: sp?.name }, sp?.name || node.type),
        el("div", { class: "cat" }, [sp?.category, sp?.family].filter(Boolean).join(" · ")))),
    el("div", { class: "insp-label" }, label),
    el("div", { class: "insp-state" },
      el("span", { class: `pill ${state}` }, STATE_LABEL[state] || state),
      st.seconds !== undefined && state === "executed" ? el("span", { class: "pill", style: { paddingLeft: "8px" } }, `${st.seconds.toFixed(2)} s`) : null,
      el("div", { class: "insp-actions" },
        el("button", { class: "btn sm", title: "Réinitialiser (F8)", onclick: () => emit("reset", [node.id]), disabled: state !== "executed" && state !== "error" }, icon("i-reset"), "Réinit."),
        el("button", { class: "btn sm primary", title: "Exécuter (F7)", onclick: () => emit("execute", [node.id]), disabled: state === "running" }, icon("i-play"), "Exécuter"))),
    state === "error" ? el("div", { class: "insp-error" }, st.message) : null,
    issues.length ? el("div", { class: "insp-msg" }, issues.join(" · ")) : null,
    (st.messages || []).length && state === "executed" ? el("div", { class: "insp-msg" }, st.messages.join("\n")) : null,
    ...leakyCvInputs(node.id).map(cvHint(node)),
  );
}

// Modèle entraîné sur une table transformée, branché sur une validation croisée.
const cvHint = (node) => ({ port, model, chain }) => {
  const name = (n) => n.label || spec(n.type)?.name || n.type;
  return el("div", { class: "insp-hint" },
    el("p", {}, t("Le modèle « {model} » a été entraîné sur la sortie de {preps}. La validation croisée réentraîne le modèle sur chaque pli, mais pas ce prétraitement : il a vu toutes les données (fuite d'information). Réunissez-les dans un Pipeline.",
      { model: name(model), preps: chain.map(name).join(" → ") })),
    el("button", { class: "btn sm primary", onclick: () => {
      if (pipelineForCv(node.id, port)) toast(t("Pipeline créé et branché sur la validation croisée"), "ok");
    } }, icon("c-compose"), t("Créer le Pipeline et l'utiliser")));
};

function tabs() {
  const mk = (id, label) => el("button", { class: tab === id ? "on" : "", onclick: () => { tab = id; render(); } }, label);
  return el("div", { class: "insp-tabs" }, mk("config", "Configuration"), mk("desc", "Description"));
}

// ---------- Formulaire ----------
function setParam(node, name, value, kind = "param") {
  if (value === undefined) delete node.params[name];
  else node.params[name] = value;
  commit(kind);
  refreshNode(node.id);
  renderEdges();
  emit("params-changed", node.id);
}

function configForm(node, sp) {
  const groups = new Map();
  for (const p of sp.params) {
    const g = p.group || "Paramètres";
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g).push(p);
  }
  const box = el("div", {});
  if (!sp.params.length) box.append(el("p", { class: "desc", style: { color: "var(--muted)" } }, "Ce nœud n'a aucun paramètre."));
  for (const [g, params] of groups) {
    const isHp = g === "Hyperparamètres";
    const groupEl = el("div", { class: "group" });
    const tools = el("div", { class: "tools" });
    if (isHp) {
      const nAdv = params.filter((p) => p.advanced).length;
      const modified = params.filter((p) => node.params[p.name] !== undefined && node.params[p.name] !== "").length;
      if (modified) tools.append(el("button", { class: "btn ghost sm", onclick: () => {
        for (const p of params) delete node.params[p.name];
        setParam(node, "__noop", undefined); render();
      } }, `Tout réinitialiser (${modified})`));
      if (nAdv) {
        const sw = el("input", { type: "checkbox", checked: showAdvanced });
        sw.addEventListener("change", () => { showAdvanced = sw.checked; render(); });
        tools.append(el("label", { class: "switch" }, sw, "Avancés"));
      }
    }
    groupEl.append(el("div", { class: "group-head" }, el("h4", {}, g), tools));
    if (isHp && params.length > 8) {
      const f = el("input", { class: "field-input hp-filter", placeholder: `Filtrer ${params.length} hyperparamètres…`, value: hpFilter });
      f.addEventListener("input", () => {
        hpFilter = f.value.toLowerCase();
        groupEl.querySelectorAll(".field[data-hp]").forEach((d) => d.classList.toggle("hidden", !!hpFilter && !d.dataset.hp.includes(hpFilter)));
      });
      groupEl.append(f);
    }
    for (const p of params) {
      if (isHp && p.advanced && !showAdvanced && node.params[p.name] === undefined) continue;
      const f = field(node, sp, p);
      if (isHp) {
        f.dataset.hp = p.name.toLowerCase();
        if (hpFilter && !f.dataset.hp.includes(hpFilter)) f.classList.add("hidden");
      }
      groupEl.append(f);
    }
    box.append(groupEl);
  }
  if (sp.doc_url) box.append(el("div", { class: "group" }, el("a", { class: "doc-link", href: sp.doc_url, target: "_blank", rel: "noopener" }, icon("i-book"), "Documentation scikit-learn", icon("i-external"))));
  return box;
}

function field(node, sp, p) {
  const isHp = p.group === "Hyperparamètres";
  const value = node.params[p.name];
  const modified = isHp && value !== undefined && value !== "";
  const wrap = el("div", { class: `field${modified ? " modified" : ""}`, dataset: { param: p.name } });
  const lab = el("div", { class: "flabel" },
    el("span", {}, p.label), p.required ? el("span", { class: "req", title: "Obligatoire" }, "*") : null,
    isHp && p.typeinfo ? el("span", { class: "typeinfo", title: p.typeinfo }, p.typeinfo.replace(/,?\s*default=.*$/, "")) : null,
    modified ? el("button", { class: "reset", title: `Revenir à la valeur par défaut (${p.default_repr})`, onclick: () => { setParam(node, p.name, undefined); render(); } }, "défaut") : null);
  wrap.append(lab);
  wrap.append(control(node, sp, p, value));
  if (p.help) {
    const h = el("div", { class: `help${isHp ? " clamp" : ""}`, title: isHp ? "Cliquer pour développer" : "" }, p.help);
    if (isHp) h.addEventListener("click", () => h.classList.toggle("clamp"));
    wrap.append(h);
  }
  return wrap;
}

function control(node, sp, p, value) {
  const isHp = p.group === "Hyperparamètres";
  const cur = value !== undefined ? value : (isHp ? undefined : p.default);
  switch (p.type) {
    case "bool": {
      const checked = cur === undefined ? !!p.default : !!cur;
      const cb = el("input", { type: "checkbox", checked });
      cb.addEventListener("change", () => setParam(node, p.name, isHp && cb.checked === p.default ? undefined : cb.checked));
      return el("label", { class: "switch" }, cb, el("span", { style: { color: "var(--text-2)", fontSize: "12px" } }, checked ? "Oui" : "Non"));
    }
    case "choice": {
      const s = el("select", { class: "field-input" });
      for (const c of p.choices) {
        const lbl = p.choice_labels?.[c] ?? (c === "" ? "(aucun)" : c);
        s.append(el("option", { value: c, selected: (cur ?? p.default) === c }, isHp && c === p.default ? `${lbl}  (défaut)` : lbl));
      }
      s.addEventListener("change", () => setParam(node, p.name, isHp && s.value === p.default ? undefined : s.value));
      return s;
    }
    case "multichoice": {
      return columnsPicker(node, p, (p.choices || []).map((c) => ({ name: c, dtype: "" })), cur || [], false);
    }
    case "int": case "float": {
      const inp = el("input", { class: "field-input", type: "number", step: p.type === "int" ? "1" : "any", value: cur ?? "", placeholder: p.allow_empty ? "(vide)" : "" });
      inp.addEventListener("input", debounce(() => {
        const v = inp.value === "" ? (p.allow_empty ? null : p.default) : p.type === "int" ? parseInt(inp.value, 10) : parseFloat(inp.value);
        setParam(node, p.name, Number.isNaN(v) ? p.default : v);
      }, 300));
      return inp;
    }
    case "code": {
      const ta = el("textarea", { class: "field-input", rows: p.rows || 4, spellcheck: "false" });
      ta.value = cur ?? "";
      ta.addEventListener("input", debounce(() => setParam(node, p.name, ta.value), 400));
      ta.addEventListener("keydown", (e) => {
        if (e.key === "Tab") { e.preventDefault(); const s = ta.selectionStart; ta.setRangeText("    ", s, ta.selectionEnd, "end"); ta.dispatchEvent(new Event("input")); }
      });
      return ta;
    }
    case "literal": {
      const listId = `dl-${node.id}-${p.name}`;
      const inp = el("input", { class: "field-input", value: cur ?? "", placeholder: p.default_repr ?? "", list: p.suggestions?.length ? listId : null, spellcheck: "false" });
      inp.style.fontFamily = "var(--mono)";
      inp.style.fontSize = "12px";
      inp.addEventListener("input", debounce(() => {
        const v = inp.value.trim();
        setParam(node, p.name, v === "" || v === p.default_repr ? undefined : v);
        inp.closest(".field")?.classList.toggle("modified", !(v === "" || v === p.default_repr));
      }, 350));
      inp.addEventListener("change", () => render());
      const out = [inp];
      if (p.suggestions?.length) out.push(el("datalist", { id: listId }, p.suggestions.map((s) => el("option", { value: s }))));
      return el("div", {}, out);
    }
    case "file":
      return fileControl(node, p, cur);
    case "column":
    case "columns":
      return columnControl(node, p, cur);
    default: {
      const inp = el("input", { class: "field-input", value: cur ?? "", spellcheck: "false" });
      inp.addEventListener("input", debounce(() => setParam(node, p.name, inp.value), 350));
      return inp;
    }
  }
}

// ---------- Sélecteurs de colonnes ----------
function knownColumns(node, port = 0) {
  return store.columns[node.id]?.[port] || null;
}

async function loadColumns(node, run) {
  const sp = spec(node.type);
  if (!sp.params.some((p) => p.type === "column" || p.type === "columns")) return;
  try {
    const res = await api.columns(wireWorkflow(), node.id, run);
    const before = JSON.stringify(store.columns[node.id] || null);
    store.columns[node.id] = res.ports;
    if (run) emit("refresh-status");
    if (JSON.stringify(res.ports) !== before && currentId === node.id) render();
  } catch (e) {
    if (run) toast(e.message, "err");
  }
}

function columnControl(node, p, cur) {
  const cols = knownColumns(node, p.port || 0);
  if (!cols) {
    const hasInput = store.wf.edges.some((e) => e.to === node.id && e.toPort === (p.port || 0));
    const box = el("div", {});
    box.append(el("div", { class: "cols-unknown" },
      hasInput ? "Colonnes inconnues : le nœud amont n'est pas exécuté." : "Connectez d'abord une table en entrée.",
      hasInput ? el("button", { class: "btn sm", onclick: (e) => { e.target.closest("button").disabled = true; loadColumns(node, true); } }, icon("i-play"), "Charger") : null));
    // Saisie manuelle possible.
    const inp = el("input", { class: "field-input", value: Array.isArray(cur) ? cur.join(", ") : cur || "", placeholder: p.type === "columns" ? "col1, col2…" : "nom de colonne" });
    inp.addEventListener("input", debounce(() => {
      const v = p.type === "columns" ? inp.value.split(",").map((s) => s.trim()).filter(Boolean) : inp.value.trim();
      setParam(node, p.name, v);
    }, 400));
    box.append(inp);
    return box;
  }
  if (p.type === "column") {
    const s = el("select", { class: "field-input", "data-raw": true });
    const blank = (allow) => el("option", { value: "" }, allow ? t("(aucune)") : t("— choisir —"));
    const allowEmpty = p.allow_empty || !p.required;
    if (allowEmpty || !cur) s.append(blank(allowEmpty));
    let found = false;
    for (const c of cols) {
      const sel = c.name === cur;
      found ||= sel;
      s.append(el("option", { value: c.name, selected: sel }, `${c.name}   · ${c.dtype}`));
    }
    if (cur && !found) s.append(el("option", { value: cur, selected: true }, `${cur} ${t("(absente)")}`));
    s.addEventListener("change", () => setParam(node, p.name, s.value));
    return s;
  }
  return columnsPicker(node, p, cols, cur || [], true);
}

function columnsPicker(node, p, cols, cur, showDtype) {
  const selected = new Set(cur);
  const filter = el("input", { placeholder: "Filtrer…" });
  const list = el("div", { class: "colpick-list" });
  const foot = el("div", { class: "colpick-foot" });
  const missing = cur.filter((c) => !cols.some((k) => k.name === c));
  const update = () => {
    const arr = [...cols.map((c) => c.name).filter((n) => selected.has(n)), ...missing.filter((m) => selected.has(m))];
    foot.textContent = arr.length ? `${arr.length} sélectionnée(s)` : (p.name === "features" || p.name === "columns" ? "Aucune sélection : toutes les colonnes utilisables" : "Aucune sélection");
    setParam(node, p.name, arr);
  };
  const draw = () => {
    const q = filter.value.toLowerCase();
    list.replaceChildren(...[...cols, ...missing.map((m) => ({ name: m, dtype: "absente" }))]
      .filter((c) => !q || c.name.toLowerCase().includes(q))
      .map((c) => {
        const cb = el("input", { type: "checkbox", checked: selected.has(c.name) });
        cb.addEventListener("change", () => { if (cb.checked) selected.add(c.name); else selected.delete(c.name); update(); });
        return el("label", {}, cb, el("span", { class: "nm", title: c.name }, c.name), showDtype && c.dtype ? el("span", { class: `dtype ${dtypeClass(c.dtype)}` }, c.dtype) : null);
      }));
  };
  filter.addEventListener("input", draw);
  const visible = () => cols.filter((c) => !filter.value || c.name.toLowerCase().includes(filter.value.toLowerCase()));
  const tools = el("div", { class: "colpick-tools" }, filter,
    el("button", { class: "btn sm", title: "Tout cocher (filtrées)", onclick: () => { visible().forEach((c) => selected.add(c.name)); draw(); update(); } }, "Tout"),
    el("button", { class: "btn sm", title: "Tout décocher", onclick: () => { selected.clear(); draw(); update(); } }, "Aucun"));
  if (showDtype && cols.some((c) => dtypeClass(c.dtype) === "num")) {
    tools.append(el("button", { class: "btn sm", title: "Cocher les colonnes numériques", onclick: () => { cols.forEach((c) => { if (dtypeClass(c.dtype) === "num") selected.add(c.name); }); draw(); update(); } }, "Num."));
  }
  draw();
  foot.textContent = selected.size ? `${selected.size} sélectionnée(s)` : (p.name === "features" || p.name === "columns" ? "Aucune sélection : toutes les colonnes utilisables" : "Aucune sélection");
  return el("div", { class: "colpick" }, tools, list, foot);
}

// ---------- Fichiers ----------
function fileControl(node, p, cur) {
  const sel = el("select", { class: "field-input" });
  const fill = () => {
    sel.replaceChildren(el("option", { value: "" }, files === null ? "Chargement…" : files.length ? "— choisir un fichier importé —" : "Aucun fichier importé"));
    for (const f of files || []) sel.append(el("option", { value: f.name, selected: f.name === cur }, `${f.name}  (${(f.size / 1024).toFixed(f.size > 1e6 ? 0 : 1)} Ko)`));
    if (cur && !(files || []).some((f) => f.name === cur)) sel.append(el("option", { value: cur, selected: true }, cur));
  };
  fill();
  if (files === null) api.files().then((r) => { files = r.files; fill(); }).catch(() => { files = []; fill(); });
  sel.addEventListener("change", () => { setParam(node, p.name, sel.value); render(); });
  const table = node.type === "io.table_reader", sql = node.type === "io.sql_reader";
  const up = el("button", { class: "btn", title: sql ? "Importer une base SQLite dans workspace/data" : table ? "Importer un fichier Parquet ou Excel dans workspace/data" : "Importer un fichier CSV dans workspace/data", onclick: () => pickAndUpload(node, p) }, icon("i-upload"), "Importer");
  const path = el("input", { class: "field-input", value: cur || "", placeholder: sql ? "…ou URL : postgresql+psycopg://utilisateur@hote/base, ou $DATABASE_URL" : table ? "…ou chemin absolu /chemin/vers/fichier.parquet" : "…ou chemin absolu /chemin/vers/fichier.csv", style: { marginTop: "6px" } });
  path.addEventListener("change", () => { setParam(node, p.name, path.value.trim()); render(); });
  return el("div", {}, el("div", { class: "field-row" }, sel, up), path);
}

export async function uploadFile(file) {
  const r = await api.upload(file);
  files = (await api.files()).files;
  toast(`« ${r.name} » importé dans workspace/data`, "ok");
  return r.name;
}

function pickAndUpload(node, p) {
  const input = document.getElementById("file-input");
  // Extensions proposées selon le lecteur (le serveur accepte tout fichier).
  input.accept = node.type === "io.table_reader" ? ".parquet,.pq,.feather,.xlsx,.xlsm,.xls"
    : node.type === "io.sql_reader" ? ".db,.sqlite,.sqlite3,.db3" : ".csv,.tsv,.txt,.data";
  input.value = "";
  input.onchange = async () => {
    const f = input.files[0];
    if (!f) return;
    try {
      const name = await uploadFile(f);
      setParam(node, p.name, name);
      render();
    } catch (e) { toast(e.message, "err"); }
  };
  input.click();
}

// ---------- Description ----------
function description(sp) {
  const d = el("div", { class: "desc" });
  if (sp.extension) d.append(el("p", { class: "pill", style: { display: "inline-flex", marginBottom: "10px" } }, `Bloc personnalisé · extension « ${sp.extension} »`));
  for (const para of (sp.description || "").split(/\n\s*\n/)) d.append(el("p", {}, para.replace(/\n/g, " ")));
  if (sp.doc_url) d.append(el("a", { class: "doc-link", href: sp.doc_url, target: "_blank", rel: "noopener" }, icon("i-book"), "Documentation scikit-learn", icon("i-external")));
  const ports = (title, list, optional = []) => list.length ? [el("h4", {}, title), el("div", { class: "ports-list" },
    list.map((p, i) => el("div", { class: "port-row" }, el("span", { class: `port-glyph ${p.kind}` }), el("span", {}, p.name),
      el("span", { class: "dtype" }, p.kind === "data" ? "table" : "modèle"), optional.includes(i) ? el("span", { class: "dtype" }, "optionnel") : null)))] : [];
  d.append(...ports("Entrées", sp.inputs, sp.optional_inputs || []), ...ports("Sorties", sp.outputs));
  const documented = sp.params.filter((p) => p.help || p.typeinfo);
  if (documented.length) {
    d.append(el("h4", {}, "Paramètres"));
    d.append(el("dl", {}, documented.map((p) => [
      el("dt", {}, p.label, p.default_repr !== undefined ? el("span", { style: { color: "var(--muted)", fontWeight: 400 } }, ` = ${p.default_repr}`) : null),
      el("dd", {}, p.typeinfo ? el("div", { style: { fontFamily: "var(--mono)", fontSize: "11px", color: "var(--muted)" } }, p.typeinfo) : null, p.help || ""),
    ])));
  }
  return d;
}

function renderTypeDescription(type) {
  if (selectedNode()) return;
  const sp = spec(type);
  if (!sp) return;
  const fam = familyOf(sp);
  root.replaceChildren(
    el("div", { class: "insp-head" },
      el("div", { class: "insp-title" },
        el("div", { class: "ico", style: { background: fam.color } }, icon(fam.icon, "")),
        el("div", { style: { minWidth: 0 } }, el("h3", {}, sp.name), el("div", { class: "cat" }, [sp.category, sp.family].filter(Boolean).join(" · ")))),
      el("div", { class: "insp-state" }, el("span", { style: { color: "var(--muted)", fontSize: "12px" } }, "Glissez ce nœud sur le canevas, ou double-cliquez pour l'ajouter."))),
    el("div", { class: "insp-body" }, description(sp)));
}
