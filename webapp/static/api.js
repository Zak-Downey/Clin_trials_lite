// The only place the page talks to the server.
export const get = (path) => send(path);
export const post = (path, body = {}) => send(path, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
});

async function send(path, options) {
  const response = await fetch(path, options);
  const body = await response.json();
  if (!response.ok) {
    const error = new Error(body.error ? body.error.message : "Request failed");
    error.kind = body.error ? body.error.kind : "unknown";
    throw error;
  }
  return body;
}

export function when(time) {
  if (!time) return "";
  // The wall clock already in `iso` (the server's zone, named in `time.zone`):
  // read it as UTC and format as UTC so the browser's own zone never shifts it.
  const m = /^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d)/.exec(time.iso);
  if (!m) return time.iso;
  const wall = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]));
  return wall.toLocaleString([], { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }) + " " + time.zone;
}
