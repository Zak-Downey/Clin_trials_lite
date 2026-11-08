// Shell and router. The URL hash holds the state: #/watchlists/<id>, #/find.
import { get } from "/static/api.js";
import { render as renderQueue } from "/static/views/needs_review.js";
import { render as renderTrial } from "/static/views/trial.js";

const sidebar = document.getElementById("sidebar");
const view = document.getElementById("view");

async function drawSidebar(activeId) {
  const { watchlists } = await get("/api/watchlists");
  sidebar.replaceChildren(...watchlists.map((w) => {
    const link = document.createElement("a");
    link.href = `#/watchlists/${w.id}/needs-review`;
    if (w.id === activeId) link.className = "active";
    const name = document.createElement("span");
    name.textContent = w.name;
    const count = document.createElement("span");
    count.className = "counts";
    const trials = `${w.trial_count} trial${w.trial_count === 1 ? "" : "s"}`;
    if (w.needs_review_count) {
      const badge = document.createElement("span");
      badge.className = "badge";
      badge.textContent = `${w.needs_review_count} to review`;
      count.append(badge, ` · ${trials}`);
    } else {
      count.textContent = `0 to review · ${trials}`;
    }
    link.append(name, count);
    return link;
  }));
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
    origin = { listId: Number(here[1]), scroll: window.scrollY };
    history.replaceState({ scroll: window.scrollY }, "");
  }
  const back = event.target.closest && event.target.closest("a[data-back]");
  if (back && origin) pendingScroll = origin.scroll;
}, true);

window.addEventListener("reviewchange", () => drawSidebar(null).catch(() => {}));

async function route() {
  const parts = location.hash.replace(/^#\/?/, "").split("/");
  document.querySelectorAll("[data-dest]").forEach((a) =>
    a.classList.toggle("active", a.dataset.dest === (parts[0] === "find" ? "find" : "watchlists")));
  try {
    if (parts[0] === "find") {
      await drawSidebar(null);
      view.textContent = "Find trials is coming.";
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
    const canonical = `#/watchlists/${id}/needs-review`;
    if (location.hash !== canonical) history.replaceState(null, "", canonical);
    await drawSidebar(id);
    await renderQueue(view, id, lists.find((w) => w.id === id));
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
