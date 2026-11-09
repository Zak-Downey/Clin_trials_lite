// Details of a trial that is not monitored: one registry fetch, nothing stored.
import { get, post } from "/static/api.js";
import { drawSections } from "/static/views/trial.js";
import { withNewEntry } from "/static/views/new_watchlist.js";

const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const kid of kids) node.append(kid);
  return node;
};

// Where the analyst came from: set by Find trials and by a New matches tab as they draw.
// back is the address "Back" returns to; list() is the watchlist to preset in Add to.
let origin = { back: "#/find", label: "‹ Back to results", list: () => null };
export function setOrigin(next) { origin = { label: "‹ Back to results", ...next }; }

export async function render(root, nct, alive = () => true) {
  const [trial, { watchlists }] = await Promise.all([get(`/api/registry/trials/${nct}`), get("/api/watchlists")]);
  if (!alive()) return; // the analyst has moved on while the registry answered
  const back = el("a", { class: "back", href: origin.back }, origin.label);
  const facts = [trial.phase, trial.sponsor, trial.status].filter(Boolean).join(" · ");
  const banner = el("div", { class: "banner", role: "status", hidden: "" });
  const pick = el("select", { id: "add-to" }, ...watchlists.map((w) => el("option", { value: String(w.id) }, w.name)));
  const came = watchlists.find((w) => w.id === origin.list());
  const first = came || watchlists.find((w) => !trial.watchlists.some((h) => h.id === w.id)) || watchlists[0];
  if (first) pick.value = String(first.id);
  withNewEntry(pick, (watchlist) => {
    pick.insertBefore(el("option", { value: String(watchlist.id) }, watchlist.name), pick.lastChild);
    pick.value = String(watchlist.id);
    window.dispatchEvent(new Event("reviewchange"));
    pick.focus({ preventScroll: true });
  });
  const add = el("button", { type: "button", class: "primary" }, "Add to watchlist");
  const problem = el("p", { class: "field-error", id: "add-error", role: "alert" });
  add.setAttribute("aria-describedby", "add-error");
  add.addEventListener("click", async () => {
    add.disabled = true;
    problem.textContent = "";
    try {
      const done = await post(`/api/watchlists/${pick.value}/trials`, { nct_ids: [nct] });
      if (done.failed.length) { problem.textContent = done.failed[0].detail; add.disabled = false; return; }
      banner.hidden = false;
      banner.className = "banner";
      const text = done.added.length ? `Added to ${done.list.name}.` : `Already in ${done.list.name}.`;
      banner.replaceChildren(el("span", {}, text, " "), el("a", { href: `#/trials/${nct}` }, "Open the trial"));
      window.dispatchEvent(new Event("reviewchange"));
    } catch (err) {
      problem.textContent = err.message;
    }
    add.disabled = false;
  });
  const holds = trial.watchlists.length ? `In: ${trial.watchlists.map((w) => w.name).join(", ")}` : "Not monitored";
  const head = el("div", { class: "trial-head" },
    el("div", {}, el("h1", {}, trial.heading), el("p", { class: "meta" }, [nct, facts, holds].filter(Boolean).join(" · "))),
    el("div", { class: "head-actions" },
      el("a", { class: "source", href: trial.registry_url, target: "_blank", rel: "noopener" }, "Open ClinicalTrials.gov ↗"),
      el("label", { for: "add-to" }, "Add to"), pick, add, problem));
  const body = el("div", { class: "trial-body" });
  root.replaceChildren(back, head, banner, body);
  drawSections(body, trial);
}
