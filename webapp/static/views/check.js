// The watchlist header and the checking status area (design pages 1 and 12).
import { get, post, when } from "/static/api.js";
import { menu as watchlistMenu } from "/static/views/watchlist_menu.js";

const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const kid of kids) node.append(kid);
  return node;
};
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
const POLL_MS = 400;

function nextLine(next) {
  if (!next) return "Finishing up";
  return next.kind === "search" ? "Searching for new matches next" : `Checking ${next.nct_id} next`;
}

function searchLine(state) {
  if (!state.has_search || !state.search) return null;
  return state.search.outcome === "error"
    ? `Saved search could not be run: ${state.search.detail}`
    : `Saved search succeeded: ${state.search.detail}`;
}

// ctx: { alive(): is this view still shown, refresh(): redraw the queue and sidebar, return the watchlist }
export function mount(headerEl, statusEl, listId, watchlist, ctx) {
  const button = el("button", { type: "button", class: "button", id: "check-button" }, "Check for updates");
  const reason = el("span", { class: "reason", id: "check-reason" });
  let current = watchlist;
  let busy = false;
  let note = ""; // why a second start did not begin, shown beside the button while the first runs

  function drawHeader() {
    const n = current.trial_count;
    // A watchlist with a saved search and no trials has one thing to check: the search.
    button.textContent = !n && current.saved_search ? "Check for new matches" : "Check for updates";
    const last = current.last_checked ? `Last checked ${when(current.last_checked)}` : "Not checked yet";
    const add = el("a", { class: "button primary", href: `#/find/${listId}` }, "Add trials");
    const more = watchlistMenu(current, {
      renamed: (renamed) => {
        current = { ...current, name: renamed.name };
        drawHeader();
        window.dispatchEvent(new Event("reviewchange")); // the sidebar carries the name too
      },
      recheck: () => begin(`/api/watchlists/${listId}/recheck`),
      changed: ctx.changed,
      deleted: ctx.deleted,
    });
    const actions = el("div", { class: "actions" }, add, button, more, reason);
    headerEl.replaceChildren(
      el("div", {},
        el("h1", {}, current.name),
        el("p", { class: "meta", id: "watchlist-meta" }, `${plural(n, "trial")} monitored · ${last}`)),
      actions);
    button.setAttribute("aria-describedby", "check-reason");
    setBusy(busy);
  }

  // aria-disabled, not disabled: a disabled button drops keyboard focus to the page.
  function setBusy(value) {
    busy = value;
    if (!busy) note = "";
    button.setAttribute("aria-disabled", String(busy));
    reason.textContent = busy ? (note || "A check is already running.") : "";
  }

  function panel(kind, children) {
    statusEl.replaceChildren(el("section", { class: `status ${kind}`, role: "status" }, ...children));
  }

  const full = (state) => state.kind === "recheck";

  function drawRunning(state) {
    const done = state.steps_done;
    const progress = el("progress", { max: String(state.steps || 1), value: String(done), "aria-label": "Check progress" });
    panel("running", [
      el("div", { class: "status-main" },
        el("h2", {}, full(state) ? "Full recheck running…" : "Checking for updates…"),
        el("p", {}, state.total ? `${state.processed} of ${state.total} trials checked · ${nextLine(state.next)}` : "Searching for new matches"),
        progress),
    ]);
  }

  function drawDone(state) {
    const incomplete = state.state === "incomplete";
    const main = el("div", { class: "status-main" });
    const side = el("div", { class: "status-side" });
    const search = searchLine(state);
    if (incomplete) {
      main.append(el("h2", {}, full(state) ? "Full recheck incomplete" : "Check incomplete"));
      const failed = state.failed ? ` · ${plural(state.failed, "trial")} could not be checked` : "";
      if (state.total) main.append(el("p", { class: "strong" }, `${state.checked} of ${state.total} trials checked${failed}`));
      if (search) main.append(el("p", { class: "search-line" }, search));
      if (state.failed) main.append(el("p", { class: "small" }, "Previous data for the failed trials are retained."));
      if (state.retryable) {
        const retry = el("button", { type: "button", class: "button" }, "Retry failed");
        retry.addEventListener("click", () => begin(`/api/watchlists/${listId}/check/retry`));
        side.append(retry);
      }
      const details = el("div", { class: "details", hidden: "" });
      const failures = state.trials.filter((t) => t.outcome === "error");
      details.append(el("ul", {}, ...failures.map((t) => el("li", {}, `${t.nct_id}: ${t.detail}`))));
      if (state.crashed) details.append(el("p", {}, `The check stopped early: ${state.crashed}`));
      const toggle = el("button", { type: "button", class: "link", "aria-expanded": "false" }, "Show details");
      toggle.addEventListener("click", () => {
        const open = details.hasAttribute("hidden");
        details.toggleAttribute("hidden", !open);
        toggle.setAttribute("aria-expanded", String(open));
        toggle.textContent = open ? "Hide details" : "Show details";
      });
      side.append(toggle);
      panel("incomplete", [main, side, details]);
      return;
    }
    const label = full(state) ? "Full recheck complete" : "Check complete";
    const headline = state.changed
      ? `${label} · ${plural(state.changed, "trial")} changed`
      : `${label} · No new changes detected`;
    main.append(el("h2", {}, headline));
    const when_ = state.finished_at ? ` at ${when(state.finished_at)}` : "";
    let line = state.total ? `${state.checked} of ${state.total} checked${when_}` : `Finished${when_}`;
    if (state.still_need_review) line += ` · ${plural(state.still_need_review, "trial")} still ${state.still_need_review === 1 ? "needs" : "need"} review from earlier checks`;
    main.append(el("p", {}, line));
    if (search) main.append(el("p", { class: "search-line" }, search));
    panel("complete", [main]);
  }

  // A check state that cannot be read is stated in words, and the button is usable again.
  function unreadable(what, err) {
    setBusy(false);
    statusEl.replaceChildren(el("div", { class: "error", role: "status" }, `${what} could not be read: ${err.message}`));
  }

  async function show() {
    let state;
    try {
      state = await get(`/api/watchlists/${listId}/check`);
    } catch (err) {
      if (ctx.alive()) unreadable("The state of the last check", err);
      return;
    }
    if (!ctx.alive()) return;
    if (state.state === "running") {
      setBusy(true);
      drawRunning(state);
      return poll();
    }
    setBusy(false);
    if (state.state === "idle") statusEl.replaceChildren();
    else drawDone(state);
  }

  async function poll() {
    while (ctx.alive()) {
      await new Promise((resolve) => setTimeout(resolve, POLL_MS));
      if (!ctx.alive()) return;
      let state;
      try {
        state = await get(`/api/watchlists/${listId}/check`);
      } catch (err) {
        if (ctx.alive()) unreadable("The check's progress", err);
        return;
      }
      if (!ctx.alive()) return;
      if (state.state === "running") { drawRunning(state); continue; }
      const fresh = await ctx.refresh();
      if (!ctx.alive()) return;
      if (fresh) current = fresh;
      setBusy(false);
      drawHeader();
      drawDone(state);
      return;
    }
  }

  async function begin(path) {
    setBusy(true);
    try {
      const state = await post(path);
      if (state.state === "running") {
        drawRunning(state);
        await poll();
      } else {
        const fresh = await ctx.refresh();
        if (fresh) current = fresh;
        setBusy(false);
        drawHeader();
        drawDone(state);
      }
    } catch (err) {
      if (err.kind === "check_running") {
        if (path.endsWith("/recheck")) note = "A check is already running, so the full recheck did not start. Run it again when this check finishes.";
        return show();
      }
      setBusy(false);
      statusEl.replaceChildren(el("div", { class: "error" }, err.message));
    }
  }

  // The watchlist's trials changed elsewhere (New matches, a removal): re-read the header.
  async function onChange() {
    if (!ctx.alive()) { window.removeEventListener("reviewchange", onChange); return; }
    try {
      const fresh = (await get("/api/watchlists")).watchlists.find((w) => w.id === Number(listId));
      if (fresh && ctx.alive()) { current = fresh; drawHeader(); }
    } catch { /* the header stays as it was */ }
  }
  window.addEventListener("reviewchange", onChange);

  button.addEventListener("click", () => { if (!busy) begin(`/api/watchlists/${listId}/check`); });
  drawHeader();
  return show();
}
