import { get, when } from "/static/api.js";

const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const kid of kids) node.append(kid);
  return node;
};

const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

export async function render(root, listId, watchlist) {
  const { trials, counts } = await get(`/api/watchlists/${listId}/needs-review`);
  const tabs = el("nav", { class: "tabs", role: "tablist", "aria-label": "Watchlist views" },
    el("a", { role: "tab", "aria-selected": "true", href: `#/watchlists/${listId}/needs-review` }, "Needs review"));
  root.replaceChildren(
    tabs,
    el("h2", { class: "queue-title", id: "queue-title" }, `${plural(counts.trials, "trial")} ${counts.trials === 1 ? "needs" : "need"} review`),
    el("p", { class: "meta", id: "queue-counts" },
      `${plural(counts.field_changes, "unreviewed field change")} · Most recently detected first`),
  );
  if (!trials.length) {
    const last = watchlist && watchlist.last_checked ? `Last checked ${when(watchlist.last_checked)}.` : "Not checked yet.";
    root.append(el("div", { class: "empty caught-up" },
      el("div", {}, el("h2", {}, "All caught up"), el("p", {}, `No changes awaiting review. ${last}`)),
      el("a", { class: "button", href: `#/watchlists/${listId}/all-trials` }, "View all trials")));
    return;
  }
  const list = el("ul", { class: "queue" });
  for (const t of trials) {
    const address = `#/trials/${t.nct_id}`;
    const identity = [t.nct_id, t.phase, t.sponsor, t.status].filter(Boolean).join(" · ");
    const body = el("div", { class: "card-body" },
      el("h3", {}, el("a", { href: address }, t.heading || t.nct_id)),
      el("p", { class: "identity" }, identity),
      el("p", { class: "fields" }, t.changed_fields.join(" · ")));
    if (t.simulated) body.append(el("p", { class: "simulated" }, "Simulated changes"));
    body.append(el("p", { class: "detected" }, `Detected ${when(t.detected_at)}`));
    const side = el("div", { class: "card-side" },
      el("span", { class: "changes" }, plural(t.change_count, "change")),
      el("a", { class: "button", href: address }, "Review changes"));
    list.append(el("li", { class: "card", "data-nct": t.nct_id }, body, side));
  }
  root.append(list);
}
