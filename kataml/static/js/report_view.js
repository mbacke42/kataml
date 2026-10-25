// Mise en page d'un rapport HTML autonome (voir kataml/report.py).

import { el } from "./ui.js";
import { renderBlocks } from "./blocks.js";
import { startTranslation } from "./i18n.js";

export function renderReport() {
  const data = JSON.parse(document.getElementById("report-data").textContent);
  const root = document.getElementById("report");
  const meta = [data.author && `Auteur : ${data.author}`, data.date, data.versions].filter(Boolean);
  root.append(
    el("button", { class: "btn toolbar-print", onclick: () => window.print() }, "Imprimer / PDF"),
    el("header", {},
      el("h1", {}, data.title),
      data.workflow && data.workflow !== data.title ? el("div", { class: "subtitle" }, `Workflow « ${data.workflow} »`) : null,
      el("div", { class: "meta" }, meta.map((m) => el("span", {}, m)))));
  if (data.notes.length) root.append(el("div", { class: "notes" }, data.notes.join("\n\n")));
  if (data.diagram) {
    const box = el("div", { class: "diagram-box" });
    box.innerHTML = data.diagram;
    root.append(box);
  }
  const titled = data.sections.filter((s) => !s.markdown || s.title);
  if (titled.length > 2) {
    root.append(el("ol", { class: "toc" }, titled.map((s) =>
      el("li", {}, el("a", { href: `#sec-${s.id}` }, s.markdown ? s.title : s.label || s.type)))));
  }
  for (const s of data.sections) {
    const sec = el("section", { class: "section", id: `sec-${s.id}` });
    root.append(sec);
    if (s.markdown) {
      if (s.title) sec.append(el("h2", {}, s.title));
    } else {
      sec.append(el("h2", {}, s.label || s.type),
        el("div", { class: "sub" }, [s.label ? s.type : null, s.category, s.seconds >= 0.05 ? `${s.seconds} s` : null].filter(Boolean).join(" · ")));
    }
    if (s.message) sec.append(el("div", { class: "warn" }, s.message));
    const view = el("div", { class: "view" });
    sec.append(view);
    renderBlocks(s.blocks, view);
  }
  if (data.code) {
    const sec = el("section", { class: "section", id: "annexe-code" }, el("h2", {}, "Annexe : script Python équivalent"),
      el("div", { class: "sub" }, "Reproduit le workflow avec pandas et scikit-learn."), el("pre", { class: "code" }, data.code));
    root.append(sec);
  }
  root.append(el("footer", {}, `Rapport généré par KataML le ${data.date}.`));
  startTranslation();
}
