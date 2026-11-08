// Shell and router. The URL hash holds the state: #/watchlists/<id>, #/find.
import { get } from "/static/api.js";
import { render as renderQueue } from "/static/views/needs_review.js";
import { mount as mountCheck } from "/static/views/check.js";

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

async function route() {
  const mine = ++generation;
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
    const watchlist = lists.find((w) => w.id === id);
    const header = el("div", { class: "watchlist-header" });
    const status = el("div", { id: "check-status" });
    const queue = el("div", { id: "queue" });
    view.replaceChildren(header, status, queue);
    await renderQueue(queue, id, watchlist);
    mountCheck(header, status, id, watchlist, {
      alive: () => generation === mine,
      refresh: async () => {
        const fresh = await drawSidebar(id);
        const current = fresh.find((w) => w.id === id);
        await renderQueue(queue, id, current);
        return current;
      },
    }).catch((err) => { if (generation === mine) status.replaceChildren(el("div", { class: "error" }, err.message)); });
  } catch (err) {
    const box = document.createElement("div");
    box.className = "error";
    box.textContent = err.message;
    view.replaceChildren(box);
  }
}

window.addEventListener("hashchange", route);
route();
