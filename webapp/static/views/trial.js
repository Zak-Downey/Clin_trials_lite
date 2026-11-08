import { get, post, when } from "/static/api.js";

const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const kid of kids) node.append(kid);
  return node;
};
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

// The trial page: header, tabs, and the Changes tab with its review action bar.
export async function render(root, nct, tab, origin) {
  const trial = await get(`/api/trials/${nct}`);
  // The list the analyst came from, else the first watchlist holding the trial.
  const home = trial.watchlists.find((w) => origin && w.id === origin.listId) || trial.watchlists[0];
  const others = trial.watchlists.filter((w) => !home || w.id !== home.id);
  const state = { reviewed: false, event: null };

  const back = el("a", { class: "back", "data-back": "", href: home ? `#/watchlists/${home.id}/needs-review` : "#/watchlists" },
    `‹ Back to ${home ? home.name : "watchlists"}`);
  const meta = [nct, trial.phase, trial.sponsor, trial.status].filter(Boolean).join(" · ");
  const title = el("div", { class: "trial-head" },
    el("div", {}, el("h1", {}, trial.heading), el("p", { class: "meta" }, meta)),
    el("a", { class: "source", href: trial.registry_url, target: "_blank", rel: "noopener" }, "Open ClinicalTrials.gov ↗"));
  const banner = el("div", { class: "banner", role: "status", hidden: "" });
  const count = el("span", { class: "tab-count" });
  const changesTab = el("a", { role: "tab", "aria-selected": String(tab === "changes"), href: `#/trials/${nct}` }, "Changes ", count);
  const tabs = el("nav", { class: "tabs", role: "tablist", "aria-label": "Trial" }, changesTab,
    el("a", { role: "tab", "aria-selected": String(tab === "details"), href: `#/trials/${nct}/details` }, "Trial details"),
    el("a", { role: "tab", "aria-selected": String(tab === "history"), href: `#/trials/${nct}/history` }, "History"));
  const body = el("div", { class: "trial-body" });
  root.replaceChildren(back, title, banner, tabs, body);

  const shown = trial.groups.flatMap((g) => g.changes);
  const ids = shown.flatMap((c) => c.ids);
  const setCount = () => { count.textContent = !state.reviewed && shown.length ? String(shown.length) : ""; };
  setCount();

  if (tab !== "changes") {
    body.append(el("div", { class: "empty" }, tab === "details" ? "Trial details are coming." : "History is coming."));
    return;
  }

  const heading = el("h2", {});
  const list = el("div", { class: "change-list" });
  const cards = [];
  for (const group of trial.groups) {
    const dates = [group.registry_updated ? `Registry updated ${group.registry_updated}` : null,
      `Detected ${when(group.detected_at)}`].filter(Boolean).join(" · ");
    const section = el("section", { class: "check-group" }, el("p", { class: "meta group-dates" }, dates));
    for (const change of group.changes) {
      const word = (q) => (q ? ` · ${q}` : "");
      // A long value gets the whole width: Previously above Now, rather than side by side.
      const long = [change.previous, change.current].some((v) => v.length > 80 || v.includes("\n"));
      const card = el("article", { class: long ? "change long" : "change" },
        el("h3", { class: "field-name" }, change.label),
        el("div", { class: "value previously" }, el("span", { class: "tag" }, "Previously"), el("p", {}, change.previous + word(change.previous_qualifier))),
        el("div", { class: "value now" }, el("span", { class: "tag" }, "Now"), el("p", {}, change.current + word(change.qualifier))));
      const label = el("span", { class: "reviewed-label", hidden: "" }, "Reviewed");
      card.prepend(label);
      cards.push(label);
      section.append(card);
    }
    list.append(section);
  }
  const headline = el("div", { class: "changes-head" }, heading);
  if (trial.simulated) headline.append(el("span", { class: "simulated-label" }, "Simulated changes"));
  body.append(headline);
  if (!shown.length) {
    heading.textContent = "No unreviewed changes";
    body.append(el("p", { class: "meta" }, "Everything detected on this trial has been reviewed. History keeps the record."));
    return;
  }
  body.append(list);

  const scope = el("strong", {});
  const also = el("span", { class: "meta" },
    others.length ? `Also clears these changes in: ${others.map((w) => w.name).join(", ")}.`
      : "No other watchlist holds this trial.");
  const next = el("button", { type: "button", class: "secondary" }, "Next trial");
  const mark = el("button", { type: "button", class: "primary" }, "Mark reviewed");
  const bar = el("div", { class: "action-bar", role: "region", "aria-label": "Review" },
    el("div", {}, scope, el("br"), also), el("div", { class: "buttons" }, next, mark));
  body.append(bar);

  const draw = () => {
    heading.textContent = state.reviewed ? `${plural(shown.length, "change")} reviewed` : `${plural(shown.length, "unreviewed change")}`;
    scope.textContent = state.reviewed ? `These ${shown.length} changes are reviewed.` : `Review covers all ${shown.length} changes shown above.`;
    cards.forEach((label) => { label.hidden = !state.reviewed; });
    mark.disabled = state.reviewed;
    setCount();
  };
  const tell = (text, undo) => {
    banner.hidden = false;
    banner.replaceChildren(el("span", {}, text));
    if (undo) banner.append(undo);
  };
  const refresh = () => window.dispatchEvent(new Event("reviewchange"));
  const fail = (err) => { banner.hidden = false; banner.className = "banner error-banner"; banner.textContent = err.message; };

  mark.addEventListener("click", async () => {
    try {
      const done = await post(`/api/trials/${nct}/review`, { ids });
      state.reviewed = true;
      state.event = done.event;
      draw();
      const undo = el("button", { type: "button", class: "link" }, "Undo");
      undo.addEventListener("click", async () => {
        try {
          await post(`/api/reviews/${done.event.id}/undo`);
          state.reviewed = false;
          state.event = null;
          draw();
          banner.hidden = true;
          refresh();
        } catch (err) { fail(err); }
      });
      tell(`${plural(shown.length, "change")} marked reviewed. This trial stays open.`, undo);
      refresh();
    } catch (err) { fail(err); }
  });

  // The queue as it stood when the page opened: Next trial goes to the one after this.
  let order = [];
  if (home) {
    try { order = (await get(`/api/watchlists/${home.id}/needs-review`)).trials.map((t) => t.nct_id); } catch { order = []; }
  }
  const at = order.indexOf(nct);
  const following = at >= 0 ? order[at + 1] : order.find((n) => n !== nct);
  if (following) next.addEventListener("click", () => { location.hash = `#/trials/${following}`; });
  else { next.disabled = true; next.title = "No other trial needs review"; }
  draw();
}
