// The watchlist's tab bar. One place, so every tab draws the same bar.
export function tabs(listId, selected) {
  const nav = document.createElement("nav");
  nav.className = "tabs";
  nav.setAttribute("role", "tablist");
  nav.setAttribute("aria-label", "Watchlist views");
  for (const [key, label] of [["needs-review", "Needs review"], ["summary", "Summary"]]) {
    const link = document.createElement("a");
    link.setAttribute("role", "tab");
    link.setAttribute("aria-selected", String(key === selected));
    link.href = `#/watchlists/${listId}/${key}`;
    link.textContent = label;
    nav.append(link);
  }
  return nav;
}
