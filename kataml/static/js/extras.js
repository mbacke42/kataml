// Boîtes de dialogue « Rapport » et « Mes blocs » (blocs personnalisés en Python).

import { accentFor } from "./theme.js";
import { el, icon, toast, openModal, closeModal, prompt, confirmBox, familyOf } from "./ui.js";
import { api } from "./api.js";
import { store, spec, nodeById, commit, topoOrder, wireWorkflow, displayState } from "./state.js";
import { render } from "./editor.js";

export function setupExtras() {}

const refreshCatalog = () => store.reloadCatalog?.();

// ---------- Rapport ----------
const includedByDefault = (n) => !!(spec(n.type)?.has_view || n.type === "report.text");
const STATE_FR = { executed: "exécuté", error: "erreur", configured: "à exécuter", unconfigured: "incomplet", running: "en cours", queued: "en attente" };

export async function reportDialog(execute) {
  if (!store.wf.nodes.length) { toast("Le workflow est vide."); return; }
  const saved = store.wf.report || {};
  const settings = { title: store.wf.name, author: "", diagram: true, notes: true, tables: true, code: false, ...saved };
  const order = topoOrder();
  let items;
  if (saved.order) {
    const kept = saved.order.filter((id) => nodeById(id));
    items = [...kept.map((id) => ({ id, on: true })), ...order.filter((id) => !kept.includes(id)).map((id) => ({ id, on: false }))];
  } else {
    items = order.map((id) => ({ id, on: includedByDefault(nodeById(id)) }));
  }
  const list = el("div", { class: "rep-nodes" });
  const drawList = () => {
    list.replaceChildren(...items.map((it, k) => {
      const n = nodeById(it.id);
      const sp = spec(n.type);
      const fam = familyOf(sp);
      const st = displayState(n);
      const cb = el("input", { type: "checkbox", checked: it.on });
      cb.addEventListener("change", () => { it.on = cb.checked; drawList(); });
      const move = (d) => {
        const j = k + d;
        if (j < 0 || j >= items.length) return;
        [items[k], items[j]] = [items[j], items[k]];
        drawList();
      };
      return el("div", { class: `rep-node${it.on ? "" : " off"}` }, cb,
        el("span", { class: "cat-dot", style: { background: fam.color } }, icon(fam.icon, "")),
        el("span", { class: "nm", title: sp?.name }, n.label || sp?.name || n.type),
        el("span", { class: "k" }, n.type === "report.text" ? "texte" : STATE_FR[st] || st),
        el("button", { class: "btn ghost sm icon", title: "Monter", onclick: () => move(-1) }, "↑"),
        el("button", { class: "btn ghost sm icon", title: "Descendre", onclick: () => move(1) }, "↓"));
    }));
  };
  drawList();
  const title = el("input", { class: "field-input", value: settings.title || "" });
  const author = el("input", { class: "field-input", value: settings.author || "", placeholder: "Facultatif" });
  const opt = (key, label) => {
    const cb = el("input", { type: "checkbox", checked: !!settings[key] });
    cb.addEventListener("change", () => { settings[key] = cb.checked; });
    return el("label", { class: "switch" }, cb, label);
  };
  const recent = el("div", { class: "wf-list" });
  api.reports().then(({ reports }) => {
    if (!reports.length) return;
    recent.replaceChildren(el("h4", {}, "Rapports récents (workspace/reports)"), ...reports.slice(0, 5).map((r) =>
      el("div", { class: "blk" }, icon("c-report"), el("div", {}, el("div", { class: "wt" }, r.name)),
        el("div", { class: "acts" },
          el("a", { class: "btn sm", href: api.reportUrl(r.name), target: "_blank", rel: "noopener" }, "Ouvrir"),
          el("a", { class: "btn sm", href: api.reportUrl(r.name, true) }, icon("i-download"))))));
  }).catch(() => {});

  const generate = async () => {
    Object.assign(settings, { title: title.value.trim() || store.wf.name, author: author.value.trim(),
      accent: accentFor("light"),
      order: items.filter((it) => it.on).map((it) => it.id) });
    store.wf.report = settings;
    commit("report");
    closeModal();
    const todo = settings.order.filter((id) => nodeById(id).type !== "report.text" && store.states[id]?.state !== "executed");
    if (todo.length) {
      toast(`Exécution de ${todo.length} nœud(s) avant le rapport…`);
      await execute(todo);
    }
    try {
      const wf = { ...wireWorkflow(), name: store.wf.name, annotations: store.wf.annotations || [] };
      const { name } = await api.report(wf, settings);
      openModal({
        title: "Rapport prêt",
        body: el("div", {}, el("p", { style: { marginTop: 0 } },
          `« ${name} » est enregistré dans workspace/reports. Ouvrez-le dans un nouvel onglet pour le lire ou l'imprimer en PDF, ou téléchargez-le : c'est un fichier HTML autonome, lisible hors ligne.`)),
        footer: [
          el("a", { class: "btn", href: api.reportUrl(name, true) }, icon("i-download"), "Télécharger"),
          el("a", { class: "btn primary", href: api.reportUrl(name), target: "_blank", rel: "noopener", onclick: () => closeModal() }, icon("i-external"), "Ouvrir le rapport"),
        ],
      });
    } catch (e) { toast(e.message, "err"); }
  };

  openModal({
    title: "Générer un rapport", wide: true,
    body: el("div", {},
      el("div", { class: "rep-grid" },
        el("div", { class: "field" }, el("label", {}, "Titre"), title),
        el("div", { class: "field" }, el("label", {}, "Auteur"), author)),
      el("div", { class: "rep-opts" },
        opt("diagram", "Schéma du workflow"), opt("notes", "Annotations"),
        opt("tables", "Aperçu des tables (nœuds sans vue)"), opt("code", "Script Python en annexe")),
      el("div", { class: "group-head" }, el("h4", {}, "Contenu et ordre des sections"),
        el("div", { class: "tools" }, el("span", {}, "Ajoutez des blocs « Texte du rapport » pour commenter."))),
      list, recent),
    footer: [el("button", { class: "btn", onclick: () => closeModal() }, "Annuler"),
             el("button", { class: "btn primary", onclick: generate }, icon("c-report"), "Générer le rapport")],
  });
}

// ---------- Mes blocs ----------
const INPUTS = {
  table: "Une table", two_tables: "Deux tables", table_model: "Un modèle et une table", none: "Aucune (bloc source)",
};

export async function blocksDialog() {
  let data;
  try { data = await api.extensions(); } catch (e) { toast(e.message, "err"); return; }
  const infoFor = (file) => data.extensions.find((x) => x.source === `fichier ${file}`);
  const files = data.files.map((f) => {
    const info = infoFor(f.name) || {};
    return el("div", { class: "blk" },
      el("span", { class: "cat-dot", style: { background: info.error ? "var(--err)" : "var(--c-ext)" } }, icon("c-ext", "")),
      el("div", { style: { minWidth: 0 } },
        el("div", { class: "wt" }, info.name || f.name),
        el("div", { class: "wd" }, `${f.name} · ${info.nodes?.length ?? 0} nœud(s)${info.description ? " · " + info.description : ""}`),
        info.error ? el("div", { class: "err" }, info.error) : null),
      el("div", { class: "acts" },
        el("button", { class: "btn sm", onclick: () => editBlock(f.name) }, "Modifier"),
        el("button", { class: "btn sm icon", title: "Supprimer", onclick: async () => {
          if (!(await confirmBox("Supprimer le bloc", `Supprimer ${f.name} ? Les nœuds de ce type deviendront inconnus.`, "Supprimer", true))) return;
          try { await api.deleteBlock(f.name); await refreshCatalog(); blocksDialog(); } catch (e) { toast(e.message, "err"); }
        } }, icon("i-trash"))));
  });
  const packages = data.extensions.filter((x) => x.source.startsWith("paquet "));
  const bundled = (data.bundled || []).map((b) => el("div", { class: "blk" },
    el("label", { class: "ext-toggle", title: b.description },
      el("input", {
        type: "checkbox", checked: b.enabled,
        onchange: async (e) => {
          const on = e.target.checked;
          try {
            await api.setBundled(b.key, on);
            await refreshCatalog();
            toast(on ? "Extension activée" : "Extension désactivée", "ok");
            blocksDialog();
          } catch (err) { e.target.checked = !on; toast(err.message, "err"); }
        },
      }), el("span", {})),
    el("div", { style: { minWidth: 0 } },
      el("div", { class: "wt" }, b.name), el("div", { class: "wd" }, b.description))));
  openModal({
    title: "Mes blocs", wide: true,
    body: el("div", {},
      el("p", { style: { marginTop: 0, color: "var(--text-2)" } },
        "Écrivez vos propres nœuds en Python : ils apparaissent dans le dépôt comme les autres. Chaque bloc est un fichier de ",
        el("code", {}, data.folder), ". Partez d'un modèle commenté, ou convertissez un nœud « Script Python » (clic droit sur le nœud)."),
      el("div", { class: "blk-list" }, files.length ? files : el("div", { class: "wd", style: { color: "var(--muted)" } }, "Aucun bloc personnalisé pour l'instant.")),
      bundled.length ? el("div", { class: "wf-list", style: { marginTop: "14px" } },
        el("h4", {}, "Extensions fournies"),
        el("p", { class: "wd", style: { color: "var(--muted)", margin: "0 0 8px" } }, "Fournies avec KataML, à activer d'un clic."),
        bundled) : null,
      packages.length ? el("div", { class: "wf-list", style: { marginTop: "14px" } }, el("h4", {}, "Extensions installées (paquets Python)"),
        packages.map((x) => el("div", { class: "blk" }, icon("c-ext"),
          el("div", {}, el("div", { class: "wt" }, `${x.name} ${x.version || ""}`), el("div", { class: "wd" }, `${x.nodes.length} nœud(s) · ${x.source}`),
            x.error ? el("div", { class: "err" }, x.error) : null)))) : null),
    footer: [
      el("button", { class: "btn", onclick: async () => {
        try { await api.reloadExtensions(); await refreshCatalog(); toast("Blocs rechargés", "ok"); blocksDialog(); } catch (e) { toast(e.message, "err"); }
      } }, icon("i-refresh"), "Recharger"),
      el("button", { class: "btn primary", onclick: newBlockDialog }, icon("i-plus"), "Nouveau bloc"),
    ],
  });
}

function newBlockDialog() {
  const name = el("input", { class: "field-input", value: "Mon bloc" });
  const desc = el("input", { class: "field-input", placeholder: "Ce que fait le bloc (affiché dans la description)" });
  const inputs = el("select", { class: "field-input" }, Object.entries(INPUTS).map(([k, v]) => el("option", { value: k }, v)));
  openModal({
    title: "Nouveau bloc",
    body: el("div", {},
      el("div", { class: "field" }, el("label", {}, "Nom"), name),
      el("div", { class: "field" }, el("label", {}, "Description"), desc),
      el("div", { class: "field" }, el("label", {}, "Entrées"), inputs),
      el("p", { class: "desc", style: { margin: 0 } }, "Un fichier Python commenté est créé ; vous le complétez ensuite dans l'éditeur.")),
    footer: [el("button", { class: "btn", onclick: () => blocksDialog() }, "Retour"),
      el("button", { class: "btn primary", onclick: async () => {
        try {
          const r = await api.newBlock({ name: name.value.trim() || "Mon bloc", description: desc.value.trim(), inputs: inputs.value });
          await refreshCatalog();
          editBlock(r.file);
        } catch (e) { toast(e.message, "err"); }
      } }, "Créer")],
  });
}

async function editBlock(file) {
  let source;
  try { source = (await api.readBlock(file)).source; } catch (e) { toast(e.message, "err"); return; }
  const ta = el("textarea", { class: "code-editor", spellcheck: "false" });
  ta.value = source;
  ta.addEventListener("keydown", (e) => {
    if (e.key === "Tab") { e.preventDefault(); ta.setRangeText("    ", ta.selectionStart, ta.selectionEnd, "end"); }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); save(); }
    e.stopPropagation();
  });
  const status = el("div", { class: "wd", style: { minHeight: "18px", marginTop: "8px" } });
  const save = async () => {
    try {
      const r = await api.saveBlock(file, ta.value);
      const info = r.extensions.find((x) => x.source === `fichier ${file}`);
      await refreshCatalog();
      if (info?.error) {
        status.replaceChildren(el("div", { class: "insp-error" }, info.error));
      } else {
        status.replaceChildren(el("span", { style: { color: "var(--ok)" } }, `Enregistré et rechargé : ${info?.nodes.length ?? 0} nœud(s).`));
      }
    } catch (e) { status.replaceChildren(el("div", { class: "insp-error" }, e.message)); }
  };
  openModal({
    title: `Modifier ${file}`, wide: true,
    body: el("div", {}, ta, status),
    footer: [el("button", { class: "btn", onclick: () => blocksDialog() }, "Retour à la liste"),
             el("button", { class: "btn primary", onclick: save }, icon("i-save"), "Enregistrer et recharger (Ctrl+S)")],
  });
}

// Remplace un nœud « Script Python » par un bloc réutilisable portant son code.
export async function convertScriptToBlock(node) {
  const name = await prompt("Convertir en bloc réutilisable", "Nom du bloc", node.label || "Mon script", "Convertir");
  if (!name) return;
  try {
    const r = await api.newBlock({ name, code: node.params?.code || "out = df", description: `Bloc créé à partir d'un script (« ${name} »).` });
    await refreshCatalog();
    const type = `ext.${r.file.replace(/\.py$/, "")}`;
    if (!spec(type)) { toast("Le bloc a été créé mais ne se charge pas : ouvrez « Mes blocs ».", "err"); return; }
    node.type = type;
    node.params = {};
    commit("structure");
    render();
    toast(`Bloc « ${name} » créé dans « Mes blocs » et utilisé à la place du script`, "ok");
  } catch (e) { toast(e.message, "err"); }
}
