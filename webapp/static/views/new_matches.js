// The New matches tab: what the saved search found that is not monitored yet.
// Not changes, not registrations: an invitation to add. Dismissing is remembered per watchlist.
import { get, post } from "/static/api.js";
import { setOrigin } from "/static/views/registry_trial.js";
import { tabs as tabBar } from "/static/views/tabs.js";

const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const kid of kids) node.append(kid);
  return node;
};
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
const CONSEQUENCE = "These trials will not be suggested again for this list.";

// What the analyst set, kept per watchlist so a redraw while a check finishes does not clear it.
const kept = new Map();

export async function render(root, listId, watchlist) {
  setOrigin({ back: location.hash, label: "‹ Back to New matches", list: () => Number(listId) });
  if (!kept.has(listId)) kept.set(listId, { showing: "new", pending: false, selected: new Set() });
  const mine = kept.get(listId);
  const selected = mine.selected;
  let outcome = null; // what the last action did, shown in the bar
  let current = watchlist;

  const refreshTabs = async () => {
    try {
      current = (await get("/api/watchlists")).watchlists.find((w) => w.id === Number(listId)) || current;
    } catch { /* the counts stay as they were */ }
    window.dispatchEvent(new Event("reviewchange"));
  };

  async function draw() {
    const tabs = tabBar(listId, "new-matches", current);
    const data = await get(`/api/watchlists/${listId}/new-matches${mine.showing === "dismissed" ? "/dismissed" : ""}`);
    const trials = data.trials;
    for (const id of [...selected]) if (!trials.some((t) => t.nct_id === id)) selected.delete(id);
    const bar = el("div", { class: "action-bar matches-bar", role: "region", "aria-label": "New matches actions" });
    const body = [];

    if (mine.showing === "dismissed") {
      const back = el("button", { type: "button", class: "link", id: "back-to-matches" }, "Back to new matches");
      back.addEventListener("click", () => { mine.showing = "new"; outcome = null; draw(); });
      body.push(el("div", { class: "matches-head" },
        el("div", {},
          el("h2", { id: "matches-title" }, plural(trials.length, "dismissed match").replace("matchs", "matches")),
          el("p", { class: "meta" }, "These will not be suggested again for this list unless you restore them.")),
        back));
      if (!trials.length) body.push(el("p", { class: "empty" }, "Nothing has been dismissed."));
      const list = el("ul", { class: "matches" });
      for (const t of trials) {
        const restore = el("button", { type: "button" }, "Restore");
        restore.setAttribute("aria-label", `Restore ${t.heading}`);
        restore.addEventListener("click", async () => {
          restore.disabled = true;
          try {
            await post(`/api/watchlists/${listId}/new-matches/restore`, { nct_ids: [t.nct_id] });
            outcome = { text: `Restored ${t.nct_id}. It is back in New matches.` };
            await refreshTabs();
          } catch (err) {
            restore.disabled = false;
            outcome = { text: `Could not restore ${t.nct_id}: ${err.message}`, failed: true };
          }
          draw();
        });
        list.append(card(t, restore));
      }
      body.push(list);
      if (outcome) body.push(el("p", { role: outcome.failed ? "alert" : "status", class: "meta" }, outcome.text));
      root.replaceChildren(tabs, ...body);
      return;
    }

    const view = el("button", { type: "button", class: "link", id: "view-dismissed" }, "View dismissed");
    view.addEventListener("click", () => { mine.showing = "dismissed"; outcome = null; selected.clear(); draw(); });
    body.push(el("div", { class: "matches-head" },
      el("div", {},
        el("h2", { id: "matches-title" }, trials.length ? plural(trials.length, "new match").replace("matchs", "matches") : "No new matches"),
        el("p", { class: "meta" }, trials.length
          ? "Not monitored yet. Select the trials you want to add."
          : data.saved_search
            ? "Matches of the saved search appear here after you check for updates."
            : "This watchlist has no saved search. Use Watch this search in Find trials.")),
      view));
    if (data.capped) {
      body.push(el("p", { class: "cap", role: "note" },
        `The saved search matched more than ${data.cap}; the first ${data.cap} are offered. Narrow the search to see the rest.`));
    }

    const boxes = [];
    const list = el("ul", { class: "matches" });
    const sync = () => {
      boxes.forEach(([box, t]) => { box.checked = selected.has(t.nct_id); box.closest("li").classList.toggle("selected", box.checked); });
      drawBar();
    };
    for (const t of trials) {
      const box = el("input", { type: "checkbox", "aria-label": `Select ${t.heading}`, "data-nct": t.nct_id });
      box.addEventListener("change", () => {
        if (box.checked) selected.add(t.nct_id); else selected.delete(t.nct_id);
        outcome = null; mine.pending = false;
        sync();
      });
      boxes.push([box, t]);
      list.append(card(t, null, box));
    }
    body.push(list);

    function drawBar() {
      if (outcome) {
        const close = el("button", { type: "button", class: "link" }, "Close");
        close.addEventListener("click", () => { outcome = null; drawBar(); });
        const parts = [el("div", { role: "status" }, outcome.text, " ", ...(outcome.link ? [outcome.link] : []))];
        if (outcome.undo) parts.push(outcome.undo);
        bar.hidden = false;
        bar.replaceChildren(...parts, close);
        return;
      }
      const n = selected.size;
      bar.hidden = n === 0;
      if (!n) { bar.replaceChildren(); return; }
      const dismiss = el("button", { type: "button", class: "secondary" }, `Dismiss ${n}`);
      const add = el("button", { type: "button", class: "primary" }, `Add ${n} to watchlist`);
      const note = el("span", { class: "meta", role: "alert" });
      add.addEventListener("click", async () => {
        add.disabled = true;
        try {
          const done = await post(`/api/watchlists/${listId}/trials`, { nct_ids: [...selected] });
          [...done.added, ...done.already].forEach((id) => selected.delete(id));
          const text = [`${done.added.length} added`, done.already.length && `${done.already.length} already in this list`,
            done.failed.length && `${done.failed.length} could not be added (${done.failed.map((f) => f.nct_id).join(", ")})`]
            .filter(Boolean).join("; ");
          outcome = { text, link: el("a", { href: `#/watchlists/${listId}/all-trials` }, "View All trials") };
          await refreshTabs();
          await draw();
        } catch (err) { add.disabled = false; note.textContent = err.message; }
      });
      dismiss.addEventListener("click", () => { mine.pending = true; drawBar(); });
      if (mine.pending) {
        const confirm = el("button", { type: "button", class: "primary", id: "confirm-dismiss" }, `Yes, dismiss ${n}`);
        const cancel = el("button", { type: "button", class: "secondary" }, "Cancel");
        cancel.addEventListener("click", () => { mine.pending = false; drawBar(); });
        confirm.addEventListener("click", async () => {
          confirm.disabled = true;
          try {
            const done = await post(`/api/watchlists/${listId}/new-matches/dismiss`, { nct_ids: [...selected] });
            selected.clear();
            mine.pending = false;
            const undo = el("button", { type: "button", class: "secondary", id: "undo-dismiss" }, "Undo");
            undo.addEventListener("click", async () => {
              undo.disabled = true;
              try {
                await post(`/api/watchlists/${listId}/new-matches/undo`, { token: done.undo_token });
                outcome = { text: `Undone. ${plural(done.dismissed.length, "trial")} back in New matches.` };
                await refreshTabs();
                draw();
              } catch (err) {
                undo.disabled = false; // the analyst is told, and can press it again
                // Written beside the button on the page now, not through drawBar: that one belongs to a drawing since replaced.
                let note = undo.parentElement.querySelector(".undo-error");
                if (!note) { note = el("div", { role: "alert", class: "meta undo-error" }); undo.before(note); }
                note.textContent = `Could not undo: ${err.message}`;
              }
            });
            outcome = { text: `${plural(done.dismissed.length, "trial")} dismissed. ${CONSEQUENCE}`, undo };
            await refreshTabs();
            await draw();
            undo.focus({ preventScroll: true }); // the Yes, dismiss the keyboard pressed is gone
          } catch (err) { confirm.disabled = false; note.textContent = err.message; }
        });
        bar.replaceChildren(el("strong", { class: "count" }, `${n} selected`),
          el("p", { class: "consequence", role: "status" }, CONSEQUENCE), note,
          el("div", { class: "buttons" }, cancel, confirm));
        confirm.focus({ preventScroll: true });
        return;
      }
      bar.hidden = false;
      bar.replaceChildren(el("strong", { class: "count" }, `${n} selected`), note,
        el("div", { class: "buttons" }, dismiss, add));
    }

    body.push(bar);
    root.replaceChildren(tabs, ...body);
    sync();
  }

  function card(t, extra, box) {
    const identity = [t.nct_id, t.phase, t.sponsor, t.status].filter(Boolean).join(" · ");
    const kids = [];
    if (box) kids.push(box);
    kids.push(el("div", { class: "card-body" },
      el("h3", {}, el("a", { href: `#/registry/${t.nct_id}` }, t.heading)),
      el("p", { class: "identity" }, identity)));
    const details = el("a", { class: "view-details", href: `#/registry/${t.nct_id}`, "aria-label": `View details: ${t.heading}` }, "View details");
    kids.push(extra ? el("div", { class: "card-side" }, extra, details) : details);
    return el("li", { class: "card match", "data-nct": t.nct_id }, ...kids);
  }

  await draw();
}
