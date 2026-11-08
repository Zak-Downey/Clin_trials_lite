// The only place the page talks to the server.
export async function get(path) {
  const response = await fetch(path);
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
  const date = new Date(time.iso);
  return date.toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) + " " + time.zone;
}
