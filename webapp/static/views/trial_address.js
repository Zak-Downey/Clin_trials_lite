const FROM = ["all-trials", "summary", "new-matches"];

export function trialHref(nct, tab = "changes", place = null) {
  const path = `#/trials/${nct}${tab && tab !== "changes" ? `/${tab}` : ""}`;
  if (!place || !place.list) return path;
  const from = FROM.includes(place.from) ? `&from=${place.from}` : "";
  return `${path}?list=${place.list}${from}`;
}

export function readPlace(hashQuery) {
  const params = new URLSearchParams(hashQuery || "");
  if (!params.has("list")) return null;
  const raw = params.get("list");
  const list = /^\d+$/.test(raw) ? Number(raw) : 0;
  const from = params.get("from");
  return { list, from: FROM.includes(from) ? from : "needs-review" };
}
