// Find trials > Add by NCT ID: look a trial up, see it, then add it. Nothing is added unseen.
import { get, post } from "/static/api.js";
import { withNewEntry } from "/static/views/new_watchlist.js";

const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const kid of kids) node.append(kid);
  return node;
};

// ctx: { lists(), destination(), setDestination(id), created(watchlist, watchlists) }
// Returns { redraw() } so a watchlist made elsewhere can be shown as the destination.
export function renderAddById(root, ctx) {
  const panel = el("section", { class: "card-panel" });
  root.append(panel);
  let found = null; // the trial shown, which is what Add adds
  let banner = null;

  function draw() {
    const input = el("input", { type: "text", id: "nct-id", autocomplete: "off", "aria-describedby": "nct-help nct-error" });
    const error = el("p", { class: "field-error", id: "nct-error", role: "alert" });
    const look = el("button", { type: "submit" }, "Look up trial");
    const pick = el("select", { id: "destination" }, ...ctx.lists().map((w) => el("option", { value: String(w.id) }, w.name)));
    if (ctx.destination() != null) pick.value = String(ctx.destination());
    const typed = input; // the value typed survives every failure
    const result = el("div", { class: "lookup-result", "aria-live": "polite" });
    const form = el("form", { novalidate: "" },
      el("div", { class: "field" }, el("label", { for: "destination" }, "Destination"), pick),
      el("div", { class: "field" }, el("label", { for: "nct-id" }, "NCT ID"),
        el("div", { class: "inline" }, input, look), error,
        el("p", { class: "help", id: "nct-help" }, "NCT followed by 8 digits. Keep this value if lookup fails.")),
      result);
    panel.replaceChildren(el("h2", {}, "Add by NCT ID"), form);
    if (banner) panel.prepend(banner);
    const showFound = () => {
      if (!found) { result.replaceChildren(el("p", { class: "next" }, "Next: confirm the trial title, then Add to watchlist.")); return; }
      const add = el("button", { type: "button", class: "primary" }, "Add to watchlist");
      add.addEventListener("click", async () => {
        add.disabled = true;
        try {
          const done = await post(`/api/watchlists/${ctx.destination()}/trials`, { nct_ids: [found.nct_id] });
          if (done.failed.length) { add.disabled = false; error.textContent = done.failed[0].detail; input.focus(); return; }
          const text = done.added.length ? `Added ${found.nct_id} to ${done.list.name}.` : `${found.nct_id} is already in ${done.list.name}.`;
          banner = el("div", { class: "banner", role: "status" }, el("span", {}, text, " "),
            el("a", { href: `#/watchlists/${done.list.id}/needs-review` }, `Open ${done.list.name}`));
          found = null;
          window.dispatchEvent(new Event("reviewchange"));
          draw();
          panel.querySelector("#nct-id").focus({ preventScroll: true });
        } catch (err) { add.disabled = false; error.textContent = err.message; input.focus(); }
      });
      result.replaceChildren(el("div", { class: "card found" },
        el("div", { class: "card-body" },
          el("h3", {}, found.heading),
          el("p", { class: "identity" }, found.nct_id),
          found.official_title ? el("p", {}, found.official_title) : "",
          el("p", { class: "meta" }, `Sponsor: ${found.sponsor || "Not reported"}`),
          el("p", { class: "meta" }, `Status: ${found.status}`)),
        el("div", { class: "card-side" }, add)));
    };
    showFound();
    input.addEventListener("input", () => { if (found) { found = null; showFound(); } });
    pick.addEventListener("change", () => {
      if (pick.value === "new") return;
      ctx.setDestination(Number(pick.value));
      found = null; error.textContent = ""; showFound();
    });
    withNewEntry(pick, (watchlist, all) => {
      ctx.created(watchlist, all);
      found = null;
      draw();
      panel.querySelector("#destination").focus({ preventScroll: true });
    });
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      error.textContent = "";
      banner = null; found = null; showFound();
      panel.querySelector(".banner")?.remove();
      if (ctx.destination() == null) { error.textContent = "Choose a destination watchlist first."; input.focus(); return; }
      look.disabled = true;
      try {
        found = await get(`/api/watchlists/${ctx.destination()}/lookup?nct_id=${encodeURIComponent(typed.value)}`);
        showFound();
      } catch (err) {
        error.textContent = err.message;
        input.focus();
      }
      look.disabled = false;
    });
    return input;
  }
  draw();
  return { redraw: draw };
}
