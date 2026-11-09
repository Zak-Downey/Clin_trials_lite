// The watchlist's tab bar. One place, so every tab draws the same bar.
// watchlist (optional) is the overview entry; with it, each tab but Summary carries its count.
export function tabs(listId, selected, watchlist) {
  const nav = document.createElement("nav");
  nav.className = "tabs";
  nav.setAttribute("role", "tablist");
  nav.setAttribute("aria-label", "Watchlist views");
  const counts = watchlist ? {
    "needs-review": watchlist.needs_review_count,
    "all-trials": watchlist.trial_count,
    "new-matches": watchlist.new_match_count,
  } : {};
  for (const [key, label] of [["needs-review", "Needs review"], ["all-trials", "All trials"], ["new-matches", "New matches"], ["summary", "Summary"]]) {
    const link = document.createElement("a");
    link.setAttribute("role", "tab");
    link.setAttribute("aria-selected", String(key === selected));
    link.href = `#/watchlists/${listId}/${key}`;
    link.append(label);
    if (counts[key] !== undefined) {
      const count = document.createElement("span");
      count.className = "tab-count";
      count.textContent = String(counts[key]);
      link.append(" ", count);
    }
    nav.append(link);
  }
  return nav;
}
