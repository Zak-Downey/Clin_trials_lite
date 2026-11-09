import { get, when } from "/static/api.js";
import { tabs as tabBar } from "/static/views/tabs.js";

const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const kid of kids) node.append(kid);
  return node;
};

const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

export async function render(root, listId, watchlist) {
  const { trials, counts } = await get(`/api/watchlists/${listId}/needs-review`);
  const tabs = tabBar(listId, "needs-review", watchlist);
  root.replaceChildren(
    tabs,
    el("h2", { class: "queue-title", id: "queue-title" }, `${plural(counts.trials, "trial")} ${counts.trials === 1 ? "needs" : "need"} review`),
    el("p", { class: "meta", id: "queue-counts" },
      `${plural(counts.field_changes, "unreviewed field change")} · Most recently detected first`),
  );
  if (!trials.length) {
    const last = watchlist && watchlist.last_checked ? `Last checked ${when(watchlist.last_checked)}.` : "Not checked yet.";
    // A trial whose latest check failed is not known to be unchanged: an empty queue is no all-clear then.
    let failed = 0;
    try { failed = (await get(`/api/watchlists/${listId}/all-trials`)).trials.filter((t) => t.check_failed).length; } catch { /* the card falls back to its plain wording */ }
    const body = failed
      ? [el("h3", {}, "Nothing to review yet"),
        el("p", {}, `${plural(failed, "trial")} could not be checked, so this list may be out of date. See All trials for which.`)]
      : [el("h3", {}, "All caught up"), el("p", {}, `No changes awaiting review. ${last}`)];
    root.append(el("div", { class: "card caught-up" },
      el("div", { class: "card-body" }, ...body),
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
