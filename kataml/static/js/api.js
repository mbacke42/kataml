// Client de l'API locale. Le jeton est injecté dans la page par le serveur.

const TOKEN = document.querySelector('meta[name="kataml-token"]').content;
export const LANG = (() => { try { return localStorage.getItem("kataml.lang") || "fr"; } catch { return "fr"; } })();
document.documentElement.lang = LANG;

async function request(path, body, method = "POST") {
  const res = await fetch(`/api/${path}`, {
    method,
    headers: { "Content-Type": "application/json", "X-KataML-Token": TOKEN, "X-KataML-Lang": LANG },
    body: method === "POST" ? JSON.stringify(body || {}) : undefined,
  });
  let data;
  try { data = await res.json(); } catch { data = { error: `Réponse invalide (${res.status})` }; }
  if (!res.ok || (data && data.error && data.ok === undefined)) {
    throw new Error(data.error || `Erreur ${res.status}`);
  }
  return data;
}

export const api = {
  catalog: () => request(`catalog?lang=${encodeURIComponent(LANG)}`, null, "GET"),
  status: (workflow) => request("status", { workflow }),
  execute: (workflow, node) => request("execute", { workflow, node }),
  reset: (nodes) => request("reset", { nodes }),
  columns: (workflow, node, run = false) => request("columns", { workflow, node, run }),
  columnsAll: (workflow) => request("columns_all", { workflow }),
  port: (node, port, opts = {}) => request("port", { node, port, ...opts }),
  profile: (node, port) => request("profile", { node, port }),
  view: (node) => request("view", { node }),
  files: () => request("files", null, "GET"),
  workflows: () => request("workflows", null, "GET"),
  loadWorkflow: (q) => request("workflow/load", q),
  saveWorkflow: (name, workflow) => request("workflow/save", { name, workflow }),
  shutdown: () => request("shutdown"),
  update: () => request("update", null, "GET"),
  importScript: (payload) => request("import_script", Array.isArray(payload) ? { files: payload } : payload),
  scripts: () => request("scripts", null, "GET"),
  readScript: (file) => request("script/read", { file }),
  saveScript: (file, source) => request("script/save", { file, source }),
  deleteScript: (file) => request("script/delete", { file }),
  deleteData: (file) => request("data/delete", { file }),
  exportCode: (workflow, name, format = "py") => request("export", { workflow, name, format }),
  cancel: () => request("cancel"),
  report: (workflow, options) => request("report", { workflow, options }),
  reports: () => request("reports", null, "GET"),
  reportUrl: (name, download = false) =>
    `/api/report_file?name=${encodeURIComponent(name)}&download=${download ? 1 : 0}&token=${encodeURIComponent(TOKEN)}`,
  extensions: () => request("extensions", null, "GET"),
  reloadExtensions: () => request("extensions/reload"),
  setBundled: (key, enabled) => request("bundled/set", { key, enabled }),
  newBlock: (spec) => request("extension/new", spec),
  readBlock: (file) => request("extension/read", { file }),
  saveBlock: (file, source) => request("extension/save", { file, source }),
  deleteBlock: (file) => request("extension/delete", { file }),
  components: () => request("components", null, "GET"),
  loadComponent: (id) => request("component/load", { id }),
  saveComponent: (component) => request("component/save", { component }),
  deleteComponent: (id) => request("component/delete", { id }),
  downloadUrl: (node, port, name) =>
    `/api/download?node=${encodeURIComponent(node)}&port=${port}&name=${encodeURIComponent(name)}&token=${encodeURIComponent(TOKEN)}`,
  async upload(file) {
    const res = await fetch(`/api/upload?name=${encodeURIComponent(file.name)}`, {
      method: "POST", headers: { "X-KataML-Token": TOKEN }, body: file,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Échec de l'import");
    return data;
  },
};
