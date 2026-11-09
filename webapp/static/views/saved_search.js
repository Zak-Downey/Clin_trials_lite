// Saved search: the "Watch this search" dialog (from Find trials), the banner a watchlist
// carries, and Manage saved search (Edit search, Turn off).
import { get, post } from "/static/api.js";
import { openDialog } from "/static/views/dialog.js";
import { newWatchlistDialog } from "/static/views/new_watchlist.js";
import { summary, toParams } from "/static/views/find.js";

const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const kid of kids) node.append(kid);
  return node;
};

// The query as the dialogs show it: a main line, and the narrowing filters under it.
function queryBox(q, className = "query-box") {
  const lines = summary(q);
  return el("div", { class: className }, el("strong", {}, lines.main || "Any trial"),
    lines.side ? el("div", { class: "meta" }, lines.side) : "");
}

const asText = (q) => {
  const lines = summary(q);
  return [lines.main, lines.side].filter(Boolean).join(" · ");
};

// opener: the "Watch this search" button. q: the submitted query (page shape).
// where: { lists(): watchlists, destination(): id, created(watchlist, all) } so a watchlist made
// from here becomes the destination of the Find trials view behind.
export function watchSearchDialog(opener, q, where) {
  const pick = el("select", { id: "watch-destination" });
  const fill = () => {
    pick.replaceChildren(...where.lists().map((w) => el("option", { value: String(w.id) }, w.name)));
    pick.value = String(where.destination());
    if (pick.selectedIndex < 0) pick.selectedIndex = 0;
  };
  fill();
  const create = el("button", { type: "button", class: "link", id: "watch-create" }, "+ Create a new watchlist");
  const existing = el("div", { class: "replace-warning", role: "status" });
  const error = el("p", { class: "field-error", role: "alert" });
  const cancel = el("button", { type: "button" }, "Cancel");
  const save = el("button", { type: "submit", class: "primary" }, "Watch this search");
  save.disabled = true;
  const form = el("form", { novalidate: "" },
    el("p", { class: "help" }, "Find new matches whenever you check this watchlist for updates. You choose which matches to add."),
    queryBox(q),
    el("div", { class: "field" }, el("label", { for: "watch-destination" }, "Watchlist"), pick), create,
    existing, error, el("div", { class: "dialog-actions" }, cancel, save));
  const body = el("div", {}, form);
  const { dialog, close } = openDialog(opener, "Watch this search", [body], pick);
  cancel.addEventListener("click", close);

  let asked = 0; // the answer to an earlier choice of watchlist is never shown for a later one
  const check = async () => {
    const mine = ++asked;
    save.disabled = true;
    existing.replaceChildren();
    error.textContent = "";
    if (!pick.value) return;
    try {
      const { saved_search: have } = await get(`/api/watchlists/${pick.value}/saved-search`);
      if (mine !== asked) return;
      if (have) {
        existing.replaceChildren(el("strong", {}, "This watchlist already has a saved search."),
          el("div", { class: "meta" }, `Current: ${asText(have)}`));
      }
      save.textContent = have ? "Replace saved search" : "Watch this search";
      save.disabled = false;
    } catch (err) {
      if (mine === asked) error.textContent = err.message;
    }
  };
  pick.addEventListener("change", check);
  check();

  create.addEventListener("click", () => newWatchlistDialog(create, (made, all) => {
    where.created(made, all);
    fill();
    pick.value = String(made.id);
    check();
    pick.focus({ preventScroll: true });
  }));

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    save.disabled = true;
    error.textContent = "";
    const listId = pick.value;
    try {
      const done = await post(`/api/watchlists/${listId}/saved-search`, { query: q });
      const open = el("a", { class: "button primary", href: `#/watchlists/${done.watchlist.id}/needs-review` }, "Open watchlist →");
      open.addEventListener("click", close);
      const finish = el("button", { type: "button" }, "Close");
      finish.addEventListener("click", close);
      body.replaceChildren(el("div", { class: "saved-note", role: "status" },
        el("h3", {}, "Search saved"),
        el("p", {}, `${done.watchlist.name} will check for new matches when you run Check for updates.`)),
      el("div", { class: "dialog-actions" }, finish, open));
      open.focus({ preventScroll: true });
      window.dispatchEvent(new Event("reviewchange"));
    } catch (err) {
      error.textContent = err.message;
      save.disabled = false;
    }
  });
  return dialog;
}

// Manage saved search for one watchlist. onChange() runs after Turn off.
export async function manageDialog(opener, watchlist, onChange) {
  let have = null;
  let failure = "";
  try { have = (await get(`/api/watchlists/${watchlist.id}/saved-search`)).saved_search; } catch (err) { failure = err.message; }
  const close = el("button", { type: "button" }, "Close");
  const content = [];
  let first = close;
  if (failure) content.push(el("p", { class: "field-error", role: "alert" }, failure));
  else if (!have) content.push(el("p", {}, `${watchlist.name} has no saved search.`));
  else {
    const edit = el("a", { class: "button", href: `#/find/${watchlist.id}?${toParams(have, 1)}` }, "Edit search");
    const off = el("button", { type: "button", class: "danger" }, "Turn off");
    const note = el("p", { class: "field-error", role: "alert" });
    content.push(
      el("p", { class: "help" }, `${watchlist.name} runs this search when you check for updates. New matches need your approval.`),
      queryBox(have),
      el("p", { class: "help" }, "Edit search opens Find trials with this query; the saved search changes only when you save a new one. Turn off keeps every trial in the watchlist."),
      note);
    first = edit;
    content.push(el("div", { class: "dialog-actions" }, off, edit));
    off.addEventListener("click", async () => {
      off.disabled = true;
      try {
        await post(`/api/watchlists/${watchlist.id}/saved-search/off`);
        dialog.close();
        onChange();
      } catch (err) { note.textContent = err.message; off.disabled = false; }
    });
    edit.addEventListener("click", () => dialog.close());
  }
  content.push(el("div", { class: "dialog-actions" }, close));
  const { dialog } = openDialog(opener, "Manage saved search", content, first);
  close.addEventListener("click", () => dialog.close());
}

// The banner above a watchlist's tabs. onChange() redraws the watchlist.
export function banner(watchlist, onChange) {
  const manage = el("button", { type: "button", class: "link", id: "manage-saved-search" }, "Manage");
  manage.addEventListener("click", () => manageDialog(manage, watchlist, onChange));
  return el("section", { class: "saved-banner", "aria-label": "Saved search" },
    el("strong", {}, "Saved search is on"),
    el("span", {}, "It runs when you check for updates. New matches need your approval."), manage);
}
