// Shell and router. The URL hash holds the state: #/watchlists/<id>, #/find.
import { get } from "/static/api.js";
import { render as renderQueue } from "/static/views/needs_review.js";

const sidebar = document.getElementById("sidebar");
const view = document.getElementById("view");

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
    link.href = `#/watchlists/${w.id}/needs-review`;
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
      view.textContent = `Trial ${parts[1]} is coming.`;
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
  } catch (err) {
    const box = document.createElement("div");
    box.className = "error";
    box.textContent = err.message;
    view.replaceChildren(box);
  }
}

window.addEventListener("hashchange", route);
route();
