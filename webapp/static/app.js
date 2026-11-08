// Shell and router. The URL hash holds the state: #/watchlists/<id>, #/find.
import { get } from "/static/api.js";
import { render as renderFind } from "/static/views/find.js";
import { render as renderAll } from "/static/views/all_trials.js";
import { render as renderQueue } from "/static/views/needs_review.js";
import { render as renderSummary } from "/static/views/summary.js";
import { mount as mountCheck } from "/static/views/check.js";
import { render as renderTrial } from "/static/views/trial.js";
import { render as renderRegistryTrial } from "/static/views/registry_trial.js";

const sidebar = document.getElementById("sidebar");
const view = document.getElementById("view");
let generation = 0; // a view whose number is not the latest has been left: its timers stop

const el = (tag, attrs = {}) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  return node;
};

async function drawSidebar(activeId) {
  const { watchlists } = await get("/api/watchlists");
  const heading = document.createElement("h2");
  heading.className = "sidebar-title";
  heading.textContent = "Your watchlists";
  const note = document.createElement("p");
  note.className = "sidebar-note";
  note.textContent = "Number badges show trials with unreviewed changes.";
  sidebar.replaceChildren(heading, ...watchlists.map((w) => {
    const link = document.createElement("a");
    link.href = `#/watchlists/${w.id}`; // the tab is the remembered one, else Needs review
    if (w.id === activeId) link.className = "active";
    const name = document.createElement("span");
    name.className = "name";
    name.textContent = w.name;
    const trials = document.createElement("span");
    trials.className = "counts";
    trials.textContent = `${w.trial_count} trial${w.trial_count === 1 ? "" : "s"}`;
    const badge = document.createElement("span");
    badge.className = "badge" + (w.needs_review_count ? "" : " none");
    badge.textContent = String(w.needs_review_count);
    badge.title = `${w.needs_review_count} to review`;
    link.append(name, trials, badge);
    return link;
  }), note);
  return watchlists;
}

// Where the analyst came from, so the trial page can say "Back to <watchlist>" and the
// queue can be put back at the same scroll position. Kept in the page and in the queue
// entry's history state (which is what browser Back and Forward read).
let origin = null;
let pendingScroll = null;

document.addEventListener("click", (event) => {
  const link = event.target.closest && event.target.closest('a[href^="#/trials/"]');
  const here = /^#\/watchlists\/(\d+)\//.exec(location.hash);
  if (link && here) {
    origin = { listId: Number(here[1]), tab: location.hash.split("/")[3] || "needs-review", scroll: window.scrollY };
    history.replaceState({ scroll: window.scrollY }, "");
  }
  const back = event.target.closest && event.target.closest("a[data-back]");
  if (back && origin) pendingScroll = origin.scroll;
}, true);

window.addEventListener("reviewchange", () => drawSidebar(null).catch(() => {}));

const remembered = (id) => {
  try { return localStorage.getItem(`tab:${id}`); } catch { return null; }
};
const remember = (id, tab) => {
  try { localStorage.setItem(`tab:${id}`, tab); } catch { /* the choice just is not kept */ }
};

async function route() {
  const mine = ++generation;
  const [hashPath, hashQuery = ""] = location.hash.replace(/^#\/?/, "").split("?");
  const parts = hashPath.split("/");
  document.querySelectorAll("[data-dest]").forEach((a) =>
    a.classList.toggle("active", a.dataset.dest === (parts[0] === "find" || parts[0] === "registry" ? "find" : "watchlists")));
  try {
    if (parts[0] === "find") {
      await drawSidebar(null);
      await renderFind(view, hashQuery, Number(parts[1]) || null);
      return;
    }
    if (parts[0] === "registry" && parts[1]) {
      await drawSidebar(null);
      await renderRegistryTrial(view, parts[1].toUpperCase());
      window.scrollTo(0, 0);
      return;
    }
    if (parts[0] === "trials" && parts[1]) {
      await drawSidebar(null);
      await renderTrial(view, parts[1].toUpperCase(), parts[2] || "changes", origin);
      window.scrollTo(0, 0);
      return;
    }
    const lists = await drawSidebar(null);
    const id = parts[0] === "watchlists" && parts[1] ? Number(parts[1]) : (lists[0] && lists[0].id);
    if (id === undefined) { view.textContent = "No watchlists yet."; return; }
    // The address always names the watchlist and the tab, so reload and Back land where you were.
    // A tab chosen is remembered per watchlist; a bare address opens the remembered one,
    // else Needs review. A count that changes never changes the tab.
    const known = ["needs-review", "all-trials", "summary"];
    const tab = known.includes(parts[2]) ? parts[2] : (remembered(id) || "needs-review");
    remember(id, tab);
    const canonical = `#/watchlists/${id}/${tab}`;
    if (tab !== "summary" && location.hash !== canonical) history.replaceState(null, "", canonical);
    if (tab === "summary" && !parts[2]) history.replaceState(null, "", canonical);
    const draw = tab === "summary"
      ? (node, listId, current) => renderSummary(node, listId, current, hashQuery)
      : tab === "all-trials" ? renderAll : renderQueue;
    await drawSidebar(id);
    const watchlist = lists.find((w) => w.id === id);
    const header = el("div", { class: "watchlist-header" });
    const status = el("div", { id: "check-status" });
    const queue = el("div", { id: "queue" });
    view.replaceChildren(header, status, queue);
    await draw(queue, id, watchlist);
    mountCheck(header, status, id, watchlist, {
      alive: () => generation === mine,
      refresh: async () => {
        const fresh = await drawSidebar(id);
        const current = fresh.find((w) => w.id === id);
        await draw(queue, id, current);
        return current;
      },
    }).catch((err) => { if (generation === mine) status.replaceChildren(el("div", { class: "error" }, err.message)); });
    const y = pendingScroll ?? (history.state && history.state.scroll);
    pendingScroll = null;
    if (y) window.scrollTo(0, y);
  } catch (err) {
    const box = document.createElement("div");
    box.className = "error";
    box.textContent = err.message;
    view.replaceChildren(box);
  }
}

window.addEventListener("hashchange", route);
route();
