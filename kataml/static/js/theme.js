// Apparence : mode clair / sombre, couleur principale, fond du canevas.
//
// Les préférences sont gardées dans le navigateur (localStorage « kataml.theme »).
// Un fichier theme.css placé dans l'espace de travail peut redéfinir toutes les variables
// CSS (charte d'un établissement) ; la couleur « Par défaut » est alors la sienne.

import { closeModal, el, openModal } from "./ui.js";

// Couleur principale : une teinte pour le mode clair, une plus lumineuse pour le sombre.
export const ACCENTS = {
  teal: { label: "Sarcelle", light: "#0f766e", dark: "#2dd4bf" },
  blue: { label: "Bleu", light: "#1d4ed8", dark: "#60a5fa" },
  green: { label: "Vert", light: "#15803d", dark: "#4ade80" },
  indigo: { label: "Indigo", light: "#4f46e5", dark: "#8b84ff" },
  orange: { label: "Orange", light: "#c2410c", dark: "#fb923c" },
  raspberry: { label: "Framboise", light: "#be185d", dark: "#f472b6" },
  slate: { label: "Ardoise", light: "#334155", dark: "#94a3b8" },
};
const MODES = { auto: "Automatique", light: "Clair", dark: "Sombre" };
const CANVAS = { dots: "Points", grid: "Grille", plain: "Uni" };
const DEFAULTS = { mode: "auto", accent: "default", custom: "#0f766e", canvas: "dots" };
const KEY = "kataml.theme";

let theme = load();
let onChange = () => {};
const media = matchMedia("(prefers-color-scheme: dark)");

function load() {
  let v = null;
  try { v = JSON.parse(localStorage.getItem(KEY)); } catch { /* stockage indisponible */ }
  if (v === "light" || v === "dark") v = { mode: v };          // ancien format : "light" | "dark"
  return { ...DEFAULTS, ...(v && typeof v === "object" ? v : {}) };
}

function save() {
  try { localStorage.setItem(KEY, JSON.stringify(theme)); } catch { /* stockage indisponible */ }
}

export const resolvedMode = () => (theme.mode === "auto" ? (media.matches ? "dark" : "light") : theme.mode);

// Mélange une couleur #rrggbb avec du blanc (part = proportion de blanc).
function lighten(hex, part) {
  const n = parseInt(hex.slice(1), 16);
  const c = [n >> 16, (n >> 8) & 255, n & 255].map((v) => Math.round(v + (255 - v) * part));
  return "#" + c.map((v) => v.toString(16).padStart(2, "0")).join("");
}

function luminance(hex) {
  const n = parseInt(hex.slice(1), 16);
  const lin = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
  return 0.2126 * lin(n >> 16) + 0.7152 * lin((n >> 8) & 255) + 0.0722 * lin(n & 255);
}

// Couleur principale choisie pour un mode donné, ou null (couleur de la feuille de style).
export function accentFor(mode) {
  if (theme.accent === "custom" && /^#[0-9a-f]{6}$/i.test(theme.custom)) {
    return mode === "dark" && luminance(theme.custom) < 0.25 ? lighten(theme.custom, 0.4) : theme.custom;
  }
  return ACCENTS[theme.accent]?.[mode] || null;
}

// Couleur principale de la feuille de style (app.css ou theme.css), sans le choix de l'utilisateur.
function stylesheetAccent() {
  const root = document.documentElement;
  const saved = root.style.getPropertyValue("--accent");
  root.style.removeProperty("--accent");
  const v = getComputedStyle(root).getPropertyValue("--accent").trim();
  if (saved) root.style.setProperty("--accent", saved);
  return v || "#0f766e";
}

export function applyTheme() {
  const root = document.documentElement;
  const mode = resolvedMode();
  root.dataset.theme = mode;
  root.dataset.canvas = theme.canvas;
  const accent = accentFor(mode);
  if (accent) {
    root.style.setProperty("--accent", accent);
    // Texte sur la couleur principale : blanc ou presque noir, selon le meilleur contraste.
    const l = luminance(accent);
    root.style.setProperty("--on-accent", 1.05 / (l + 0.05) >= (l + 0.05) / 0.055 ? "#fff" : "#0f0f14");
  } else {
    root.style.removeProperty("--accent");
    root.style.removeProperty("--on-accent");
  }
  document.querySelector('[data-action="theme"] use')?.setAttribute("href", mode === "dark" ? "#i-sun" : "#i-moon");
  onChange();
}

export function initTheme(changed) {
  onChange = changed || onChange;
  media.addEventListener("change", () => { if (theme.mode === "auto") applyTheme(); });
  applyTheme();
}

function update(patch) {
  theme = { ...theme, ...patch };
  save();
  applyTheme();
}

// Bascule rapide clair / sombre (bouton lune / soleil).
export function toggleMode() {
  update({ mode: resolvedMode() === "dark" ? "light" : "dark" });
}

export function themeDialog() {
  const body = el("div", { class: "theme-dlg" });
  const seg = (options, key) => el("div", { class: "seg" }, Object.entries(options).map(([k, label]) =>
    el("button", { class: theme[key] === k ? "on" : "", onclick: () => { update({ [key]: k }); draw(); } }, label)));
  const draw = () => {
    const mode = resolvedMode();
    const swatch = (key, color, label, extra = "") => el("button", {
      class: `swatch${extra}${theme.accent === key ? " on" : ""}`, title: label, "aria-label": label,
      style: { background: color }, onclick: () => { update({ accent: key }); draw(); },
    });
    const picker = el("input", { type: "color", value: theme.custom, title: "Couleur personnalisée" });
    picker.addEventListener("input", () => update({ accent: "custom", custom: picker.value }));
    picker.addEventListener("change", draw);
    body.replaceChildren(
      el("div", {}, el("h4", {}, "Mode"), seg(MODES, "mode"),
        el("p", { class: "hint" }, "« Automatique » suit le réglage clair / sombre du système.")),
      el("div", {}, el("h4", {}, "Couleur principale"),
        el("div", { class: "swatches" },
          swatch("default", stylesheetAccent(), "Par défaut", " default"),
          Object.entries(ACCENTS).map(([k, a]) => swatch(k, a[mode], a.label)),
          el("label", { class: `swatch-custom${theme.accent === "custom" ? " on" : ""}` }, picker, "Personnalisée")),
        el("p", { class: "hint" }, "Boutons, sélection, liens et onglets actifs. La couleur des familles de nœuds ne change pas.")),
      el("div", {}, el("h4", {}, "Fond du canevas"), seg(CANVAS, "canvas")),
      el("p", { class: "hint", style: { margin: 0 } },
        "Pour aller plus loin, un fichier theme.css placé dans l'espace de travail peut redéfinir toutes les couleurs de l'interface et des rapports (variables CSS)."));
  };
  draw();
  openModal({
    title: "Apparence", body,
    footer: [
      el("button", { class: "btn", onclick: () => { theme = { ...DEFAULTS }; save(); applyTheme(); draw(); } }, "Réinitialiser"),
      el("button", { class: "btn primary", onclick: () => closeModal() }, "Fermer"),
    ],
  });
}
