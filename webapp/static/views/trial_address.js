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
// A list that is not a watchlist number (list=abc, list=0, an empty list=) names no watchlist that can
// hold the trial: it reads as list 0, so the trial page falls back and rewrites it like a wrong number.
export function readPlace(hashQuery) {
  const params = new URLSearchParams(hashQuery || "");
  if (!params.has("list")) return null;
  const raw = params.get("list");
  const list = /^\d+$/.test(raw) ? Number(raw) : 0;
  const from = params.get("from");
  return { list, from: FROM.includes(from) ? from : "needs-review" };
}
