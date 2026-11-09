// Find trials: the Search tab. The address (#/find?cond=...&page=2) holds the submitted query.
import { get, post } from "/static/api.js";
import { withNewEntry } from "/static/views/new_watchlist.js";
import { renderAddById } from "/static/views/add_by_id.js";
import { watchSearchDialog } from "/static/views/saved_search.js";
import { setOrigin } from "/static/views/registry_trial.js";

const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const kid of kids) node.append(kid);
  return node;
};

const PHASES = [["EARLY_PHASE1", "Early phase 1", "Early phase 1"], ["PHASE1", "1", "Phase 1"], ["PHASE2", "2", "Phase 2"],
  ["PHASE3", "3", "Phase 3"], ["PHASE4", "4", "Phase 4"], ["NA", "Not applicable", "Not applicable"]];
const SPONSOR_TYPES = [["INDUSTRY", "Industry"], ["OTHER", "Other (incl. academic)"], ["NIH", "NIH"],
  ["FED", "US federal"], ["OTHER_GOV", "Other government"], ["NETWORK", "Network"], ["INDIV", "Individual"]];
const STATUSES = [["NOT_YET_RECRUITING", "Not yet recruiting"], ["RECRUITING", "Recruiting"],
  ["ENROLLING_BY_INVITATION", "Enrolling by invitation"], ["ACTIVE_NOT_RECRUITING", "Active, not recruiting"],
  ["SUSPENDED", "Suspended"], ["TERMINATED", "Terminated"], ["COMPLETED", "Completed"],
  ["WITHDRAWN", "Withdrawn"], ["UNKNOWN", "Unknown"]];
const NAMING = "Start with at least one of these four fields";

// Kept across renders, so selections survive paging, viewing a trial and leaving Find trials.
const selected = new Map(); // NCT ID -> title
let destination = null; // the watchlist chosen to add to
let cameFrom = null; // the watchlist whose "Add trials" opened Find trials last
let outcome = null; // what the last add did, shown in the bar until the next selection
let lastFind = "#/find"; // where "Back to results" goes

// A watchlist made elsewhere (the sidebar) becomes the destination; the open view, if it
// shows one, is told so it can redraw its picker without being rebuilt.
let refreshDestination = () => {};
export function chooseDestination(id) {
  destination = id;
  refreshDestination();
}

const name = (table, code) => (table.find((row) => row[0] === code) || [code, code])[1];
const number = (n) => n.toLocaleString("en-US");

function readQuery(params) {
  return {
    cond: params.get("cond") || "", intr: params.get("intr") || "", spons: params.get("spons") || "",
    phase: params.getAll("phase"), sponsor_type: params.getAll("sponsor_type"), status: params.getAll("status"),
    started_from: params.get("started_from") || "", started_to: params.get("started_to") || "",
  };
}

export function toParams(q, page) {
  const p = new URLSearchParams();
  for (const k of ["cond", "intr", "spons"]) if (q[k].trim()) p.set(k, q[k].trim());
  for (const k of ["phase", "sponsor_type", "status"]) q[k].forEach((v) => p.append(k, v));
  for (const k of ["started_from", "started_to"]) if (q[k]) p.set(k, q[k]);
  if (page) p.set("page", String(page));
  return p;
}

const named = (q) => q.cond.trim() || q.intr.trim() || q.spons.trim() || q.phase.length;

export function summary(q) {
  const main = [q.cond.trim(), q.intr.trim() && `Intervention ${q.intr.trim()}`, q.spons.trim(),
    q.phase.length && q.phase.map((c) => name(PHASES.map((p) => [p[0], p[2]]), c)).join("/")].filter(Boolean);
  const side = [q.sponsor_type.length && q.sponsor_type.map((c) => name(SPONSOR_TYPES, c)).join(" or "),
    q.status.length && q.status.map((c) => name(STATUSES, c)).join(" or "),
    q.started_from && `Started on or after ${q.started_from}`, q.started_to && `Started on or before ${q.started_to}`].filter(Boolean);
  return { main: main.join(" · "), side: side.join(" · ") };
}

function field(label, key, value) {
  const id = `find-${key}`;
  const input = el("input", { id, name: key, type: "text", autocomplete: "off" });
  input.value = value;
  return el("div", { class: "field" }, el("label", { for: id }, label), input);
}

function form(q, error, onSubmit, datesError = "") {
  const phases = new Set(q.phase);
  const phaseButtons = PHASES.map(([code, text, full]) => {
    const b = el("button", { type: "button", class: "toggle", "aria-pressed": String(phases.has(code)), "aria-label": full, "data-code": code }, text);
    b.addEventListener("click", () => b.setAttribute("aria-pressed", String(b.getAttribute("aria-pressed") !== "true")));
    return b;
  });
  const sponsorBoxes = SPONSOR_TYPES.map(([code, text]) => {
    const box = el("input", { type: "checkbox", name: "sponsor_type", value: code });
    box.checked = q.sponsor_type.includes(code);
    return el("label", { class: "check" }, box, text);
  });
  const statusBoxes = STATUSES.map(([code, text]) => {
    const box = el("input", { type: "checkbox", name: "status", value: code });
    box.checked = q.status.includes(code);
    return el("label", { class: "check" }, box, text);
  });
  const dates = [["Study started from", "started_from"], ["Study started to", "started_to"]].map(([text, key]) => {
    const input = el("input", { id: `find-${key}`, name: key, type: "date" });
    input.value = q[key];
    return el("div", { class: "field" }, el("label", { for: `find-${key}` }, text), input);
  });
  const more = el("div", { id: "more-filters", hidden: "" },
    el("div", { class: "filters" },
      el("fieldset", { class: "statuses" }, el("legend", {}, "Lead sponsor type"), ...sponsorBoxes,
        el("p", { class: "help" }, "Sponsor type uses the lead sponsor, not collaborators")),
      el("fieldset", { class: "statuses" }, el("legend", {}, "Trial status"), ...statusBoxes),
      el("div", { class: "dates" }, ...dates,
        el("p", { class: "help" }, "Date filters exclude trials without a reported start date"),
        ...(datesError ? [el("p", { class: "field-error", role: "alert" }, datesError)] : []))));
  const toggle = el("button", { type: "button", class: "link", "aria-expanded": "false", "aria-controls": "more-filters" }, "More filters");
  toggle.addEventListener("click", () => {
    const open = more.hasAttribute("hidden");
    more.toggleAttribute("hidden", !open);
    toggle.setAttribute("aria-expanded", String(open));
  });
  if (q.sponsor_type.length || q.status.length || q.started_from || q.started_to) toggle.click();
  const group = el("fieldset", { class: "naming" }, el("legend", { id: "naming-rule" }, NAMING),
    el("div", { class: "fields" }, field("Condition", "cond", q.cond), field("Intervention", "intr", q.intr), field("Sponsor", "spons", q.spons)),
    el("div", { class: "field" }, el("span", { class: "label", id: "phase-label" }, "Phase"),
      el("div", { class: "phases", role: "group", "aria-labelledby": "phase-label" }, ...phaseButtons)));
  if (error) group.append(el("p", { class: "field-error", role: "alert" }, error));
  const clear = el("button", { type: "button", class: "link" }, "Clear all");
  const submit = el("button", { type: "submit", class: "primary" }, "Search trials");
  const f = el("form", { class: "search-form", novalidate: "" }, group, toggle, more, el("div", { class: "actions" }, clear, submit));
  const read = () => ({
    cond: f.cond.value, intr: f.intr.value, spons: f.spons.value,
    phase: phaseButtons.filter((b) => b.getAttribute("aria-pressed") === "true").map((b) => b.dataset.code),
    sponsor_type: sponsorBoxes.map((l) => l.firstChild).filter((b) => b.checked).map((b) => b.value),
    status: statusBoxes.map((l) => l.firstChild).filter((b) => b.checked).map((b) => b.value),
    started_from: f.started_from.value, started_to: f.started_to.value,
  });
  clear.addEventListener("click", () => {
    f.reset();
    for (const k of ["cond", "intr", "spons"]) f[k].value = "";
    sponsorBoxes.forEach((l) => { l.firstChild.checked = false; });
    f.started_from.value = ""; f.started_to.value = "";
    statusBoxes.forEach((l) => { l.firstChild.checked = false; });
    phaseButtons.forEach((b) => b.setAttribute("aria-pressed", "false"));
  });
  f.addEventListener("submit", (event) => { event.preventDefault(); onSubmit(read()); });
  return f;
}

function results(q, data, page, go, edit, clearOptional, changed, watch) {
  const out = el("section", { class: "results", "aria-label": "Search results" });
  const head = summary(q);
  out.append(el("div", { class: "summary" },
    el("div", {}, el("strong", { id: "query-summary" }, head.main || "Search"), head.side ? el("div", { class: "meta" }, head.side) : ""),
    el("div", { class: "summary-actions" }, watch, edit)));
  if (!data.total) {
    const again = el("button", { type: "button" }, "Edit search");
    again.addEventListener("click", () => edit.click());
    out.append(el("div", { class: "empty" }, el("p", {}, "No trials match this search."), el("div", { class: "actions" }, again, clearOptional)));
    return out;
  }
  const first = (page - 1) * data.page_size + 1;
  out.append(el("h2", { id: "match-count" }, `${number(data.total)} match${data.total === 1 ? "" : "es"}`),
    el("p", { class: "meta", id: "range" }, `${first}–${first + data.rows.length - 1} of ${number(data.total)} matches`));
  if (data.capped) out.append(el("p", { class: "cap", role: "note" }, `Showing the first 100 of ${number(data.total)}. Narrow your search to see the rest`));
  const list = el("ul", { class: "cards" });
  const boxes = [];
  const everyOne = el("input", { type: "checkbox", id: "select-page" });
  const sync = () => {
    boxes.forEach(([box, r]) => { box.checked = selected.has(r.nct_id); box.closest("li").classList.toggle("selected", box.checked); });
    everyOne.checked = boxes.every(([box]) => box.checked);
  };
  everyOne.addEventListener("change", () => {
    for (const [, r] of boxes) { if (everyOne.checked) selected.set(r.nct_id, r.title || r.nct_id); else selected.delete(r.nct_id); }
    outcome = null;
    sync();
    changed();
  });
  out.append(el("div", { class: "select-page" }, el("label", { for: "select-page" }, everyOne, ` Select ${data.rows.length} on this page`)));
  for (const r of data.rows) {
    const facts = [r.phase, r.sponsor, r.status].filter(Boolean).join(" · ");
    const title = r.title || r.nct_id;
    const box = el("input", { type: "checkbox", "aria-label": `Select ${title}`, "data-nct": r.nct_id });
    box.addEventListener("change", () => {
      if (box.checked) selected.set(r.nct_id, title); else selected.delete(r.nct_id);
      outcome = null;
      sync();
      changed();
    });
    boxes.push([box, r]);
    list.append(el("li", { class: "card result", "data-nct": r.nct_id }, box,
      el("div", { class: "result-body" }, el("strong", {}, title), el("div", { class: "meta" }, `${facts} · ${r.nct_id}`)),
      el("a", { class: "view-details", href: `#/registry/${r.nct_id}`, "aria-label": `View details: ${title}` }, "View details")));
  }
  sync();
  const prev = el("button", { type: "button" }, "Previous");
  const next = el("button", { type: "button" }, "Next");
  prev.disabled = page <= 1;
  next.disabled = page >= data.pages;
  prev.addEventListener("click", () => go(page - 1));
  next.addEventListener("click", () => go(page + 1));
  out.append(list, el("nav", { class: "pager", "aria-label": "Result pages" }, prev, el("span", {}, `Page ${page} of ${data.pages}`), next));
  return out;
}

// alive(): is this still the page the address names? A slow answer for a page the analyst left is dropped.
export async function render(root, search, listId, tab = "search", alive = () => true) {
  const base = listId ? `#/find/${listId}` : "#/find";
  refreshDestination = () => {};
  if (tab === "id") lastFind = base;
  else lastFind = location.hash || base;
  if (listId && listId !== cameFrom) destination = listId;
  cameFrom = listId || null;
  setOrigin({ back: lastFind, list: () => destination });
  let lists = [];
  try { lists = (await get("/api/watchlists")).watchlists; } catch { lists = []; }
  if (!alive()) return;
  if (!lists.some((w) => w.id === destination)) destination = lists[0] ? lists[0].id : null;
  const created = (watchlist, all) => {
    lists = all;
    destination = watchlist.id;
    window.dispatchEvent(new Event("reviewchange"));
    drawBar();
    const again = root.querySelector("#add-to");
    if (again) again.focus({ preventScroll: true });
  };
  const tabBar = () => el("nav", { class: "tabs", role: "tablist", "aria-label": "Find trials views" },
    el("a", { role: "tab", "aria-selected": String(tab === "search"), href: base }, "Search"),
    el("a", { role: "tab", "aria-selected": String(tab === "id"), href: `${base}/id` }, "Add by NCT ID"));
  const syncChecks = () => {
    const boxes = [...root.querySelectorAll("li.result input[type=checkbox]")];
    boxes.forEach((box) => { box.checked = selected.has(box.dataset.nct); box.closest("li").classList.toggle("selected", box.checked); });
    const all = root.querySelector("#select-page");
    if (all) all.checked = boxes.every((b) => b.checked);
  };
  const bar = el("div", { class: "action-bar find-bar", role: "region", "aria-label": "Add selected trials" });
  const drawBar = () => {
    if (outcome) {
      const dismiss = el("button", { type: "button", class: "link" }, "Dismiss");
      dismiss.addEventListener("click", () => { outcome = null; drawBar(); });
      bar.hidden = false;
      bar.replaceChildren(el("div", { role: "status" }, outcome.text, " ",
        el("a", { href: `#/watchlists/${outcome.list.id}/needs-review` }, `Open ${outcome.list.name}`)), dismiss);
      return;
    }
    bar.hidden = selected.size === 0;
    if (!selected.size) { bar.replaceChildren(); return; }
    const count = `${selected.size} trial${selected.size === 1 ? "" : "s"}`;
    const clear = el("button", { type: "button", class: "link" }, "Clear");
    clear.addEventListener("click", () => { selected.clear(); drawBar(); syncChecks(); });
    const pick = el("select", { id: "add-to" }, ...lists.map((w) => el("option", { value: String(w.id) }, w.name)));
    pick.value = String(destination);
    pick.addEventListener("change", () => { if (pick.value !== "new") destination = Number(pick.value); });
    withNewEntry(pick, created);
    const add = el("button", { type: "button", class: "primary" }, `Add ${count}`);
    const note = el("span", { class: "meta", role: "alert" });
    add.addEventListener("click", async () => {
      add.disabled = true;
      try {
        const done = await post(`/api/watchlists/${destination}/trials`, { nct_ids: [...selected.keys()] });
        if (done.failed.length && !done.added.length && !done.already.length) {
          add.disabled = false;
          note.textContent = `${done.failed.length} could not be added. ${done.failed.map((f) => f.detail).filter(Boolean).join(" ")}`;
          return;
        }
        [...done.added, ...done.already].forEach((n) => selected.delete(n));
        const text = [`${done.added.length} added`, done.already.length && `${done.already.length} already in this list`,
          done.failed.length && `${done.failed.length} could not be added (${done.failed.map((f) => f.nct_id).join(", ")})`]
          .filter(Boolean).join("; ");
        outcome = { text, list: done.list };
        window.dispatchEvent(new Event("reviewchange"));
        drawBar();
        syncChecks();
      } catch (err) { add.disabled = false; note.textContent = err.message; }
    });
    bar.hidden = false;
    bar.replaceChildren(el("strong", { class: "count" }, `${count} selected`), clear, note,
      el("label", { for: "add-to" }, "Add to"), pick, add);
  };
  if (tab === "id") {
    root.replaceChildren(el("h1", {}, "Find trials"), el("p", { class: "meta" }, "Search ClinicalTrials.gov, then choose what to monitor."), tabBar());
    const handle = renderAddById(root, {
      lists: () => lists, destination: () => destination,
      setDestination: (id) => { destination = id; },
      created: (watchlist, all) => { lists = all; destination = watchlist.id; window.dispatchEvent(new Event("reviewchange")); },
    });
    refreshDestination = () => get("/api/watchlists").then((r) => { lists = r.watchlists; handle.redraw(); }).catch(() => {});
    return;
  }
  refreshDestination = () => {
    if (!lists.some((w) => w.id === destination)) {
      get("/api/watchlists").then((r) => { lists = r.watchlists; drawBar(); }).catch(() => {});
    } else drawBar();
  };
  drawBar();
  const params = new URLSearchParams(search || "");
  const q = readQuery(params);
  const page = Math.max(1, Number(params.get("page")) || 1);
  const submitted = named(q) && (params.has("page") || params.has("cond") || params.has("intr") || params.has("spons") || params.has("phase"));
  const rerender = () => render(root, search, listId, tab, alive);
  const head = [el("h1", {}, "Find trials"), el("p", { class: "meta" }, "Search ClinicalTrials.gov, then choose what to monitor."),
    tabBar()];
  const open = (query, error, below, datesError = "") => {
    root.replaceChildren(...head, form(query, error, (typed) => {
      if (!named(typed)) { open(typed, "Add a condition, intervention, sponsor or phase to search.", below); return; }
      const target = `${base}?${toParams(typed, 1)}`;
      if (location.hash === target) rerender(); else location.hash = target;
    }, datesError));
    if (below) root.append(below);
    root.append(bar);
  };
  if (!submitted) { open(q, "", null); return; }
  const status = el("p", { class: "meta", role: "status" }, "Searching…");
  root.replaceChildren(...head, status);
  let data;
  try {
    data = await get(`/api/search?${toParams(q, page)}`);
  } catch (err) {
    if (!alive()) return;
    // A refusal is the analyst's to fix: the message sits beside its fields, the form open, no Retry.
    if (err.kind === "nothing_asked") { open(q, err.message, null); return; }
    if (err.kind === "bad_dates") { open(q, "", null, err.message); return; }
    const retry = el("button", { type: "button" }, "Retry");
    retry.addEventListener("click", rerender);
    open(q, "", el("div", { class: "error", role: "alert" }, el("p", {}, err.message), retry));
    return;
  }
  if (!alive()) return;
  const edit = el("button", { type: "button" }, "Edit search");
  edit.addEventListener("click", () => open(q, "", null));
  const clearOptional = el("button", { type: "button" }, "Clear optional filters");
  clearOptional.addEventListener("click", () => {
    location.hash = `${base}?${toParams({ ...q, sponsor_type: [], status: [], started_from: "", started_to: "" }, 1)}`;
  });
  const watch = el("button", { type: "button", id: "watch-search" }, "Watch this search");
  watch.addEventListener("click", () => watchSearchDialog(watch, q, { lists: () => lists, destination: () => destination, created }));
  root.replaceChildren(...head, results(q, data, page, (p) => { location.hash = `${base}?${toParams(q, p)}`; }, edit, clearOptional, drawBar, watch), bar);
}
