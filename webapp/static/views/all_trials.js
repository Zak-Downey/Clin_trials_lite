import { get, when } from "/static/api.js";
import { tabs as tabBar } from "/static/views/tabs.js";

const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const kid of kids) node.append(kid);
  return node;
};

const byText = (a, b) => a.heading.localeCompare(b.heading, "en", { sensitivity: "base" });
const SORTS = {
  title: ["Trial title", byText],
  change: ["Latest change", (a, b) =>
    (b.latest_change ? b.latest_change.iso : "").localeCompare(a.latest_change ? a.latest_change.iso : "") || byText(a, b)],
  status: ["Trial status", (a, b) => a.status.localeCompare(b.status, "en") || byText(a, b)],
};

export async function render(root, listId) {
  const { trials } = await get(`/api/watchlists/${listId}/all-trials`);
  const filter = el("input", { type: "text", id: "trial-filter", "aria-describedby": "filter-note", autocomplete: "off" });
  const sort = el("select", { id: "trial-sort" },
    ...Object.entries(SORTS).map(([key, [label]]) => el("option", { value: key }, label)));
  const tbody = el("tbody");
  const count = el("p", { class: "meta", id: "trial-count", role: "status" });
  const empty = el("p", { class: "empty", hidden: "" }, "No trials in this watchlist match that filter.");
  const table = el("table", { class: "trials" },
    el("thead", {}, el("tr", {}, ...["Trial", "Trial status", "Review", "Last successful check"].map((h) => el("th", { scope: "col" }, h)))),
    tbody);

  const draw = () => {
    const needle = filter.value.trim().toLowerCase();
    const shown = trials
      .filter((t) => !needle || [t.heading, t.nct_id, t.sponsor || ""].some((s) => s.toLowerCase().includes(needle)))
      .sort(SORTS[sort.value][1]);
    tbody.replaceChildren(...shown.map((t) => {
      const title = el("td", {}, el("a", { href: `#/trials/${t.nct_id}/details` }, t.heading),
        el("div", { class: "identity" }, [t.nct_id, t.phase, t.sponsor].filter(Boolean).join(" · ")));
      const checked = el("td", {}, t.last_checked ? when(t.last_checked) : "Not checked yet");
      if (t.check_failed) {
        checked.append(el("div", { class: "warning", role: "note" },
          `⚠ Latest check failed${t.check_failed.at ? ` (${when(t.check_failed.at)})` : ""}`));
      }
      return el("tr", { "data-nct": t.nct_id }, title, el("td", {}, t.status),
        el("td", {}, el("span", { class: `review-state ${t.review.state}` }, t.review.label)), checked);
    }));
    table.hidden = !shown.length;
    empty.hidden = !!shown.length;
    count.textContent = shown.length === trials.length
      ? `${trials.length} trial${trials.length === 1 ? "" : "s"} · All shown`
      : `${shown.length} of ${trials.length} trials`;
  };
  filter.addEventListener("input", draw);
  sort.addEventListener("change", draw);
  draw();

  root.replaceChildren(
    tabBar(listId, "all-trials"),
    el("div", { class: "table-tools" },
      el("div", { class: "field" },
        el("label", { for: "trial-filter" }, "Filter by title, NCT ID or sponsor"), filter,
        el("p", { class: "help", id: "filter-note" }, "Searches only this watchlist, not ClinicalTrials.gov. Use Find trials to search the registry.")),
      el("div", { class: "field" }, el("label", { for: "trial-sort" }, "Sort"), sort)),
    table, empty, count);
}
