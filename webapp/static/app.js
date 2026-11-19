import { get } from "/static/api.js";
import "/static/focus.js";
import { render as renderFind, chooseDestination } from "/static/views/find.js";
import { render as renderAll } from "/static/views/all_trials.js";
import { render as renderQueue } from "/static/views/needs_review.js";
import { render as renderNewMatches } from "/static/views/new_matches.js";
import { render as renderSummary } from "/static/views/summary.js";
import { mount as mountCheck } from "/static/views/check.js";
import { render as renderTrial } from "/static/views/trial.js";
import { readPlace } from "/static/views/trial_address.js";
import { newWatchlistDialog } from "/static/views/new_watchlist.js";
import { banner as savedSearchBanner } from "/static/views/saved_search.js";
import { render as renderRegistryTrial } from "/static/views/registry_trial.js";
import { menu as watchlistMenu } from "/static/views/watchlist_menu.js";

const sidebar = document.getElementById("sidebar");
const view = document.getElementById("view");
let generation = 0;

const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const kid of kids) node.append(kid);
  return node;
};

function newButton() {
  const button = el("button", { type: "button", id: "new-watchlist", class: "new-watchlist" });
  button.textContent = "+ New watchlist";
  button.addEventListener("click", () => newWatchlistDialog(button, async (made) => {
    chooseDestination(made.id);
    window.dispatchEvent(new Event("reviewchange"));
  }));
  return button;
}

let sidebarRequest = 0;
async function drawSidebar(activeId, alive = () => true) {
  const mine = ++sidebarRequest;
  const { watchlists } = await get("/api/watchlists");
  if (!alive() || mine !== sidebarRequest) return watchlists;
  if (activeId === undefined) {
    const parts = location.hash.replace(/^#\/?/, "").split("?")[0].split("/");
    activeId = parts[0] === "watchlists" ? (Number(parts[1]) || null) : null;
  }
  const heading = document.createElement("h2");
  heading.className = "sidebar-title";
  heading.textContent = "Your watchlists";
  const note = document.createElement("p");
  note.className = "sidebar-note";
  note.textContent = "Number badges show trials with unreviewed changes.";
  sidebar.replaceChildren(heading, ...watchlists.map((w) => {
    const link = document.createElement("a");
    link.href = `#/watchlists/${w.id}`;
    if (w.id === activeId) { link.className = "active"; link.setAttribute("aria-current", "page"); }
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
  }), newButton(), note);
  return watchlists;
}

let left = null;
let pendingScroll = null;

document.addEventListener("click", (event) => {
  const link = event.target.closest && event.target.closest('a[href^="#/trials/"]');
  const here = /^#\/watchlists\/\d+\/[^/?]+/.exec(location.hash);
  if (link && here) {
    left = { at: here[0], full: location.hash, scroll: window.scrollY };
    history.replaceState({ scroll: window.scrollY }, "");
  }
  const back = event.target.closest && event.target.closest("a[data-back]");
  if (back && left && [left.at, left.full].includes(back.getAttribute("href"))) pendingScroll = left.scroll;
}, true);
window.addEventListener("hashchange", (event) => {
  const was = new URL(event.oldURL).hash;
  if (left && (was === left.at || was.startsWith(`${left.at}?`))) left.full = was;
});

window.addEventListener("reviewchange", () => drawSidebar(undefined).catch(() => {}));

const remembered = (id) => {
  try { return localStorage.getItem(`tab:${id}`); } catch { return null; }
};
const remember = (id, tab) => {
  try { localStorage.setItem(`tab:${id}`, tab); } catch { }
};

function drawFirstUse(watchlist) {
  const find = el("a", { class: "button primary", href: `#/find/${watchlist.id}` });
  find.textContent = "Find trials";
  const byId = el("a", { class: "button", href: `#/find/${watchlist.id}/id` });
  byId.textContent = "Add by NCT ID";
  const title = el("h1");
  title.textContent = watchlist.name;
  const more = watchlistMenu(watchlist, {
    renamed: () => { window.dispatchEvent(new Event("reviewchange")); route(); },
    deleted: () => { location.hash = "#/watchlists"; },
  }, { basic: true });
  const actions = el("div", { class: "actions" });
  actions.append(more);
  const header = el("div", { class: "watchlist-header" });
  header.append(title, actions);
  const card = el("section", { class: "first-use", "aria-labelledby": "first-use-title" });
  const heading = el("h2", { id: "first-use-title" });
  heading.textContent = "Monitor your first trial";
  const why = el("p");
  why.textContent = "Add a trial from ClinicalTrials.gov. This saves a starting point; future checks show what has changed.";
  const buttons = el("div", { class: "actions-row" });
  buttons.append(find, byId);
  const note = el("p", { class: "help" });
  note.textContent = "You choose when to check for updates.";
  card.append(heading, why, buttons, note);
  view.replaceChildren(header, card);
}

async function route() {
  const mine = ++generation;
  const [hashPath, hashQuery = ""] = location.hash.replace(/^#\/?/, "").split("?");
  const parts = hashPath.split("/");
  document.querySelectorAll("[data-dest]").forEach((a) =>
    a.classList.toggle("active", a.dataset.dest === (parts[0] === "find" || parts[0] === "registry" ? "find" : "watchlists")));
  const alive = () => generation === mine;
  try {
    if (parts[0] === "find") {
      await drawSidebar(null, alive);
      if (!alive()) return;
      const tab = parts[1] === "id" || parts[2] === "id" ? "id" : "search";
      await renderFind(view, hashQuery, Number(parts[1]) || null, tab, alive);
      return;
    }
    if (parts[0] === "registry" && parts[1]) {
      await drawSidebar(null, alive);
      if (!alive()) return;
      await renderRegistryTrial(view, parts[1].toUpperCase(), alive);
      window.scrollTo(0, 0);
      return;
    }
    if (parts[0] === "trials" && parts[1]) {
      await drawSidebar(null, alive);
      if (!alive()) return;
      const place = readPlace(hashQuery);
      if (place && left && left.at === `#/watchlists/${place.list}/${place.from}`) place.back = left.full;
      await renderTrial(view, parts[1].toUpperCase(), parts[2] || "changes", place, alive);
      if (!alive()) return;
      window.scrollTo(0, 0);
      return;
    }
    const lists = await drawSidebar(null, alive);
    if (!alive()) return;
    const id = parts[0] === "watchlists" && parts[1] ? Number(parts[1]) : (lists[0] && lists[0].id);
    if (id === undefined) {
      view.textContent = "No watchlists yet. Use + New watchlist to make one.";
      const make = document.getElementById("new-watchlist");
      if (make && document.activeElement === document.body) make.focus({ preventScroll: true });
      return;
    }
    const known = ["needs-review", "all-trials", "summary", "new-matches"];
    const tab = known.includes(parts[2]) ? parts[2] : (remembered(id) || "needs-review");
    remember(id, tab);
    const canonical = `#/watchlists/${id}/${tab}`;
    if (tab !== "summary" && location.hash !== canonical) history.replaceState(null, "", canonical);
    if (tab === "summary" && !parts[2]) history.replaceState(null, "", canonical);
    const draw = tab === "summary"
      ? (node, listId, current) => renderSummary(node, listId, current, location.hash.split("?")[1] || "", alive)
      : tab === "all-trials" ? (node, listId, current) => renderAll(node, listId, current, alive)
        : tab === "new-matches" ? renderNewMatches : (node, listId, current) => renderQueue(node, listId, current, alive);
    await drawSidebar(id, alive);
    if (!alive()) return;
    const watchlist = lists.find((w) => w.id === id);
    if (watchlist && !watchlist.trial_count && !watchlist.saved_search) { drawFirstUse(watchlist); return; }
    const header = el("div", { class: "watchlist-header" });
    const status = el("div", { id: "check-status" });
    const queue = el("div", { id: "queue" });
    view.replaceChildren(header, ...(watchlist && watchlist.saved_search ? [savedSearchBanner(watchlist, route)] : []), status, queue);
    await draw(queue, id, watchlist);
    if (!alive()) return;
    mountCheck(header, status, id, watchlist, {
      alive,
      changed: route,
      deleted: () => { location.hash = "#/watchlists"; },
      refresh: async () => {
        const fresh = await drawSidebar(id, alive);
        const current = fresh.find((w) => w.id === id);
        if (!alive()) return current;
        await draw(queue, id, current);
        return current;
      },
    }).catch((err) => { if (generation === mine) status.replaceChildren(el("div", { class: "error" }, err.message)); });
    const y = pendingScroll ?? (history.state && history.state.scroll);
    pendingScroll = null;
    if (y) window.scrollTo(0, y);
  } catch (err) {
    if (generation !== mine) return;
    const box = document.createElement("div");
    box.className = "error";
    box.textContent = err.message;
    view.replaceChildren(box);
  }
}

window.addEventListener("hashchange", route);
route();
