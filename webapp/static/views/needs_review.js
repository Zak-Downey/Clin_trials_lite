import { get, when } from "/static/api.js";

const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const kid of kids) node.append(kid);
  return node;
};

export async function render(root, listId, watchlist) {
  const { trials, counts } = await get(`/api/watchlists/${listId}/needs-review`);
  const tabs = el("nav", { class: "tabs", role: "tablist", "aria-label": "Watchlist views" },
    el("a", { role: "tab", "aria-selected": "true", href: `#/watchlists/${listId}/needs-review` }, "Needs review"));
  root.replaceChildren(
    tabs,
    el("p", { class: "meta", id: "queue-counts" },
      `${counts.trials} trial${counts.trials === 1 ? "" : "s"} need${counts.trials === 1 ? "s" : ""} review · ` +
      `${counts.field_changes} unreviewed field change${counts.field_changes === 1 ? "" : "s"}`),
  );
  if (!trials.length) {
    const last = watchlist && watchlist.last_checked ? `Last checked ${when(watchlist.last_checked)}.` : "Not checked yet.";
    root.append(el("div", { class: "empty caught-up" },
      el("div", {}, el("h2", {}, "All caught up"), el("p", {}, `No changes awaiting review. ${last}`)),
      el("a", { class: "button", href: `#/watchlists/${listId}/all-trials` }, "View all trials")));
    return;
  }
  const table = el("table", { class: "queue" });
  table.append(el("thead", {}, el("tr", {},
    ...["Trial", "Phase", "Sponsor", "Status", "What changed", "Detected"].map((h) => el("th", {}, h)))));
  const body = el("tbody");
  for (const t of trials) {
    const address = `#/trials/${t.nct_id}`;
    const first = el("td", {}, el("strong", {}, el("a", { href: address }, t.heading || t.nct_id)),
      el("div", { class: "meta" }, t.nct_id), el("a", { href: address }, "Review changes"));
    const changed = el("td", {}, `${t.changed_fields.join(", ")} (${t.change_count})`);
    if (t.simulated) changed.append(el("div", { class: "simulated" }, "Simulated changes"));
    body.append(el("tr", { "data-nct": t.nct_id }, first, el("td", { class: "fit" }, t.phase || ""),
      el("td", {}, t.sponsor || ""), el("td", { class: "fit" }, t.status || ""), changed, el("td", {}, when(t.detected_at))));
  }
  table.append(body);
  root.append(table);
}
