// A trial's address: #/trials/<NCT>[/<tab>]?list=<watchlist id>&from=<watchlist tab>.
// `list` is the watchlist the trial was opened from and `from` its tab, left out for Needs review,
// so "Back to" and Next trial survive a reload, a new tab and a saved link.
const FROM = ["all-trials", "summary", "new-matches"];

// place: { list, from } or null for an address that names no watchlist.
export function trialHref(nct, tab = "changes", place = null) {
  const path = `#/trials/${nct}${tab && tab !== "changes" ? `/${tab}` : ""}`;
  if (!place || !place.list) return path;
  const from = FROM.includes(place.from) ? `&from=${place.from}` : "";
  return `${path}?list=${place.list}${from}`;
}

// The watchlist and tab a trial address names: { list, from } (from is "needs-review" when left out), or null.
export function readPlace(hashQuery) {
  const params = new URLSearchParams(hashQuery || "");
  const list = Number(params.get("list"));
  if (!Number.isInteger(list) || list <= 0) return null;
  const from = params.get("from");
  return { list, from: FROM.includes(from) ? from : "needs-review" };
}
