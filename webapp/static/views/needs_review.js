import { get, when } from "/static/api.js";

const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const kid of kids) node.append(kid);
  return node;
};

export async function render(root, listId, watchlist) {
  const { trials, counts } = await get(`/api/watchlists/${listId}/needs-review`);
  root.replaceChildren(
    el("h1", {}, watchlist ? watchlist.name : "Watchlist"),
    el("p", { class: "meta", id: "queue-counts" },
      `Needs review: ${counts.trials} trial${counts.trials === 1 ? "" : "s"}, ` +
      `${counts.field_changes} unreviewed field change${counts.field_changes === 1 ? "" : "s"}`),
  );
  if (!trials.length) {
    root.append(el("div", { class: "empty" }, "Nothing needs review."));
    return;
  }
  const table = el("table", { class: "queue" });
  table.append(el("thead", {}, el("tr", {},
    ...["Trial", "Phase", "Sponsor", "Status", "What changed", "Detected"].map((h) => el("th", {}, h)))));
  const body = el("tbody");
  for (const t of trials) {
    const first = el("td", {}, el("strong", {}, t.heading || t.nct_id), el("div", { class: "meta" }, t.nct_id));
    const changed = el("td", {}, `${t.changed_fields.join(", ")} (${t.change_count})`);
    if (t.simulated) changed.append(el("div", { class: "simulated" }, "Simulated"));
    body.append(el("tr", { "data-nct": t.nct_id }, first, el("td", {}, t.phase || ""),
      el("td", {}, t.sponsor || ""), el("td", {}, t.status || ""), changed, el("td", {}, when(t.detected_at))));
  }
  table.append(body);
  root.append(table);
}
