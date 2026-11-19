import { post } from "/static/api.js";
import { openDialog } from "/static/views/dialog.js";

const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const kid of kids) node.append(kid);
  return node;
};

export function newWatchlistDialog(opener, onCreated, onCancel = () => {}) {
  const input = el("input", { type: "text", id: "new-watchlist-name", autocomplete: "off", "aria-describedby": "new-watchlist-help new-watchlist-error" });
  const error = el("p", { class: "field-error", id: "new-watchlist-error", role: "alert" });
  const create = el("button", { type: "submit", class: "primary" }, "Create watchlist");
  const cancel = el("button", { type: "button" }, "Cancel");
  const form = el("form", { novalidate: "" },
    el("div", { class: "field" }, el("label", { for: "new-watchlist-name" }, "Name"), input, error),
    el("p", { class: "help", id: "new-watchlist-help" },
      "The new watchlist becomes your destination. Trials are added only when you press Add."),
    el("div", { class: "dialog-actions" }, cancel, create));
  let created = false;
  const { dialog, close } = openDialog(opener, "New watchlist", [form], input);
  dialog.addEventListener("close", () => { if (!created) onCancel(); });
  cancel.addEventListener("click", close);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    error.textContent = "";
    if (!input.value.trim()) { error.textContent = "Give the watchlist a name."; input.focus(); return; }
    create.disabled = true;
    try {
      const done = await post("/api/watchlists", { name: input.value });
      created = true;
      close();
      onCreated(done.watchlist, done.watchlists);
    } catch (err) {
      error.textContent = err.message;
      create.disabled = false;
      input.focus();
    }
  });
}

export const NEW = "new";

export function withNewEntry(select, onCreated) {
  select.append(el("option", { value: NEW }, "+ New watchlist"));
  let before = select.value;
  select.addEventListener("focus", () => { if (select.value !== NEW) before = select.value; });
  select.addEventListener("change", () => {
    if (select.value !== NEW) { before = select.value; return; }
    select.value = before;
    newWatchlistDialog(select, onCreated);
  });
}
