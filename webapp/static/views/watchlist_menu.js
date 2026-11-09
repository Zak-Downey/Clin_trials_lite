// The watchlist's ⋯ menu (design page 13): Rename, Manage saved search, Full recheck, Delete.
// Each item opens its own dialog; no dialog both creates, renames and deletes.
import { post } from "/static/api.js";
import { openDialog } from "/static/views/dialog.js";
import { manageDialog } from "/static/views/saved_search.js";

const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const kid of kids) node.append(kid);
  return node;
};

function renameDialog(opener, watchlist, onRenamed) {
  const input = el("input", { type: "text", id: "rename-watchlist-name", autocomplete: "off", "aria-describedby": "rename-watchlist-error" });
  input.value = watchlist.name;
  const error = el("p", { class: "field-error", id: "rename-watchlist-error", role: "alert" });
  const save = el("button", { type: "submit", class: "primary" }, "Save name");
  const cancel = el("button", { type: "button" }, "Cancel");
  const form = el("form", { novalidate: "" },
    el("div", { class: "field" }, el("label", { for: "rename-watchlist-name" }, "Watchlist name"), input, error),
    el("div", { class: "dialog-actions" }, cancel, save));
  const { close } = openDialog(opener, "Rename watchlist", [form], input);
  input.select();
  cancel.addEventListener("click", close);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    error.textContent = "";
    if (!input.value.trim()) { error.textContent = "Give the watchlist a name."; input.focus(); return; }
    save.disabled = true;
    try {
      const done = await post(`/api/watchlists/${watchlist.id}/rename`, { name: input.value });
      close();
      onRenamed(done.watchlist);
    } catch (err) {
      error.textContent = err.message;
      save.disabled = false;
      input.focus();
    }
  });
}

function recheckDialog(opener, onStart) {
  const start = el("button", { type: "button", class: "primary" }, "Start full recheck");
  const cancel = el("button", { type: "button" }, "Cancel");
  const { close } = openDialog(opener, "Full recheck", [
    el("p", {}, "A full recheck compares every monitored field of every trial, even when the registry's update date has not moved."),
    el("p", { class: "help" }, "It runs once, takes longer than a normal check and finishes with its own label. Normal checks keep skipping trials the registry has not updated."),
    el("div", { class: "dialog-actions" }, cancel, start),
  ], start);
  cancel.addEventListener("click", close);
  start.addEventListener("click", () => { close(); onStart(); });
}

function deleteDialog(opener, watchlist, onDeleted) {
  const error = el("p", { class: "field-error", role: "alert" });
  const remove = el("button", { type: "button", class: "danger" }, "Delete watchlist");
  const cancel = el("button", { type: "button" }, "Cancel");
  const { close } = openDialog(opener, `Delete “${watchlist.name}”?`, [
    el("p", {}, "This removes this watchlist, its saved search and its trial memberships. Trials in other watchlists are unchanged."),
    el("p", { class: "help" }, "Monitoring history is kept. Trials with no remaining watchlist stop being checked."),
    el("p", { class: "help" }, "This cannot be undone."),
    error,
    el("div", { class: "dialog-actions" }, cancel, remove),
  ], cancel);
  cancel.addEventListener("click", close);
  remove.addEventListener("click", async () => {
    remove.disabled = true;
    try {
      await post(`/api/watchlists/${watchlist.id}/delete`);
      close();
      onDeleted();
    } catch (err) {
      error.textContent = err.message;
      remove.disabled = false;
    }
  });
}

// watchlist: the current one. hooks: { renamed(watchlist), recheck(), changed(), deleted() }.
export function menu(watchlist, hooks) {
  const button = el("button", { type: "button", id: "watchlist-menu-button", class: "secondary menu-button", "aria-label": "Watchlist actions", "aria-haspopup": "menu", "aria-expanded": "false" }, "⋯");
  const list = el("div", { class: "menu", role: "menu", "aria-label": "Watchlist actions", hidden: "" });
  const close = () => { list.hidden = true; button.setAttribute("aria-expanded", "false"); };
  const item = (label, run, extra = "") => {
    const node = el("button", { type: "button", role: "menuitem", class: `menu-action ${extra}`.trim() }, label);
    node.addEventListener("click", () => { close(); run(); });
    return node;
  };
  list.append(
    item("Rename watchlist", () => renameDialog(button, watchlist, hooks.renamed)),
    item("Manage saved search", () => manageDialog(button, watchlist, hooks.changed)),
    item("Full recheck", () => recheckDialog(button, hooks.recheck)),
    item("Delete watchlist", () => deleteDialog(button, watchlist, hooks.deleted), "danger-text"));
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    list.hidden = !list.hidden;
    button.setAttribute("aria-expanded", String(!list.hidden));
    if (!list.hidden) list.querySelector("button").focus();
  });
  document.addEventListener("click", (event) => { if (!list.contains(event.target)) close(); });
  list.addEventListener("keydown", (event) => { if (event.key === "Escape") { close(); button.focus(); } });
  return el("div", { class: "menu-wrap" }, button, list);
}
