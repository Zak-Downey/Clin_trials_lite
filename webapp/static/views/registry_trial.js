// Details of a trial that is not monitored: one registry fetch, nothing stored.
import { get, post } from "/static/api.js";
import { drawSections } from "/static/views/trial.js";
import { withNewEntry } from "/static/views/new_watchlist.js";
import { lastFind } from "/static/views/find.js";

const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const kid of kids) node.append(kid);
  return node;
};

export async function render(root, nct, alive = () => true) {
  const [trial, { watchlists }] = await Promise.all([get(`/api/registry/trials/${nct}`), get("/api/watchlists")]);
  if (!alive()) return; // the analyst has moved on while the registry answered
  const back = el("a", { class: "back", href: lastFind }, "‹ Back to results");
  const facts = [trial.phase, trial.sponsor, trial.status].filter(Boolean).join(" · ");
  const banner = el("div", { class: "banner", role: "status", hidden: "" });
  const pick = el("select", { id: "add-to" }, ...watchlists.map((w) => el("option", { value: String(w.id) }, w.name)));
  const first = watchlists.find((w) => !trial.watchlists.some((h) => h.id === w.id)) || watchlists[0];
  if (first) pick.value = String(first.id);
  withNewEntry(pick, (watchlist) => {
    pick.insertBefore(el("option", { value: String(watchlist.id) }, watchlist.name), pick.lastChild);
    pick.value = String(watchlist.id);
    window.dispatchEvent(new Event("reviewchange"));
    pick.focus({ preventScroll: true });
  });
  const add = el("button", { type: "button", class: "primary" }, "Add to watchlist");
  add.addEventListener("click", async () => {
    add.disabled = true;
    try {
      const done = await post(`/api/watchlists/${pick.value}/trials`, { nct_ids: [nct] });
      banner.hidden = false;
      banner.className = "banner";
      const text = done.failed.length ? done.failed[0].detail
        : done.added.length ? `Added to ${done.list.name}.` : `Already in ${done.list.name}.`;
      banner.replaceChildren(el("span", {}, text, " "), el("a", { href: `#/trials/${nct}` }, "Open the trial"));
      window.dispatchEvent(new Event("reviewchange"));
    } catch (err) {
      banner.hidden = false;
      banner.className = "banner error-banner";
      banner.textContent = err.message;
    }
    add.disabled = false;
  });
  const holds = trial.watchlists.length ? `In: ${trial.watchlists.map((w) => w.name).join(", ")}` : "Not monitored";
  const head = el("div", { class: "trial-head" },
    el("div", {}, el("h1", {}, trial.heading), el("p", { class: "meta" }, [nct, facts, holds].filter(Boolean).join(" · "))),
    el("div", { class: "head-actions" },
      el("a", { class: "source", href: trial.registry_url, target: "_blank", rel: "noopener" }, "Open ClinicalTrials.gov ↗"),
      el("label", { for: "add-to" }, "Add to"), pick, add));
  const body = el("div", { class: "trial-body" });
  root.replaceChildren(back, head, banner, body);
  drawSections(body, trial);
}
