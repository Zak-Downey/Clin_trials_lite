// The Summary tab (design page 10): a period, a heading, trials grouped by check, Copy and Export.
import { get, when } from "/static/api.js";
import { tabs } from "/static/views/tabs.js";

const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const kid of kids) node.append(kid);
  return node;
};
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
const PERIODS = [["week", "This week"], ["month", "This month"], ["custom", "Custom dates"]];

// The platform's clipboard and download, bound once here and passed as bare functions.
const writeClipboard = (text) => navigator.clipboard.writeText(text);

function download(name, text) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/csv;charset=utf-8" }));
  const link = el("a", { href: url, download: name });
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function queryOf(period) {
  return period.kind === "custom"
    ? `period=custom&from=${period.from}&to=${period.to}` : `period=${period.kind}`;
}

function valueLine(change) {
  const side = (v, q) => (q ? `${v} (${q})` : v);
  return `${side(change.previous, change.previous_qualifier)} → ${side(change.current, change.qualifier)}`;
}

function trialCard(trial) {
  const open = el("details", { class: "trial-moves" });
  open.append(el("summary", {}, `View ${plural(trial.change_count, "change")} →`));
  for (const check of trial.checks) {
    const list = el("ul", { class: "moves" });
    for (const c of check.changes) {
      const row = el("li", { class: "move" },
        el("strong", {}, c.label), ` ${valueLine(c)} `,
        el("span", { class: "state" }, c.reviewed ? "Reviewed" : "Awaiting review"));
      if (c.simulated) row.append(" ", el("span", { class: "state simulated" }, "Simulated"));
      list.append(row);
    }
    open.append(el("h4", { class: "check-head" }, `Detected ${when(check.detected_at)}`), list);
  }
  const head = el("div", { class: "trial-head" },
    el("h3", {}, el("a", { href: `#/trials/${trial.nct_id}` }, trial.heading)),
    el("span", { class: "changes" }, plural(trial.change_count, "change")));
  const card = el("li", { class: "card trial", "data-nct": trial.nct_id },
    el("div", { class: "card-body" }, head,
      el("p", { class: "identity" },
        `${trial.nct_id} · `, el("a", { href: trial.url, target: "_blank", rel: "noopener" }, "ClinicalTrials.gov"),
        ` · ${plural(trial.check_count, "check")} with changes`),
      el("p", {}, trial.latest),
      open));
  if (trial.simulated) card.querySelector(".card-body").append(el("p", { class: "simulated" }, "Simulated changes"));
  return card;
}

export async function render(root, listId, watchlist, hashQuery = "") {
  const params = new URLSearchParams(hashQuery);
  let period = { kind: ["week", "month", "custom"].includes(params.get("period")) ? params.get("period") : "week" };
  if (period.kind === "custom") {
    period.from = params.get("from"); period.to = params.get("to");
    if (!period.from || !period.to) period = { kind: "week" };
  }
  let data = await get(`/api/watchlists/${listId}/summary?${queryOf(period)}`);
  let editing = false; // the Custom dates form is open
  let notice = "";

  const body = el("div", { class: "summary-body" });
  root.replaceChildren(tabs(listId, "summary", watchlist), body);

  const remember = () => history.replaceState(history.state, "", `#/watchlists/${listId}/summary?${queryOf(period)}`);

  async function choose(next) {
    const fresh = await get(`/api/watchlists/${listId}/summary?${queryOf(next)}`);
    period = next; data = fresh; editing = false; notice = "";
    remember();
    draw();
  }

  function periodButtons() {
    const row = el("div", { class: "periods", role: "group", "aria-label": "Period" });
    for (const [kind, label] of PERIODS) {
      const pressed = kind === "custom" ? (editing || period.kind === "custom") : period.kind === kind;
      const button = el("button", { type: "button", class: "toggle", "aria-pressed": String(pressed) }, label);
      button.addEventListener("click", () => {
        if (kind === "custom") { editing = true; draw(); return; }
        choose({ kind }).catch(showError);
      });
      row.append(button);
    }
    return row;
  }

  function customForm() {
    const from = el("input", { type: "date", id: "summary-from", value: period.kind === "custom" ? period.from : data.period.start });
    const to = el("input", { type: "date", id: "summary-to", value: period.kind === "custom" ? period.to : data.period.end });
    const problem = el("p", { class: "field-error", role: "alert" });
    const apply = el("button", { type: "button", class: "primary" }, "Apply");
    const cancel = el("button", { type: "button" }, "Cancel");
    apply.addEventListener("click", async () => {
      problem.textContent = "";
      if (!from.value || !to.value) { problem.textContent = "Enter both a From and a To date."; return; }
      if (from.value > to.value) { problem.textContent = "The From date must not be after the To date."; return; }
      try { await choose({ kind: "custom", from: from.value, to: to.value }); }
      catch (err) { problem.textContent = err.message; }
    });
    cancel.addEventListener("click", () => { editing = false; draw(); });
    return el("form", { class: "custom-dates", novalidate: "" },
      el("div", { class: "field" }, el("label", { for: "summary-from" }, "From"), from),
      el("div", { class: "field" }, el("label", { for: "summary-to" }, "To"), to),
      el("div", { class: "form-actions" }, apply, cancel), problem);
  }

  function showError(err) {
    notice = err.message;
    draw();
  }

  function showNotice() {
    let node = body.querySelector("#summary-notice");
    if (!node) {
      node = el("p", { class: "help", role: "status", id: "summary-notice" });
      body.querySelector("#summary-heading").before(node);
    }
    node.textContent = notice;
  }

  function outputs() {
    const empty = data.counts.field_changes === 0;
    const copy = el("button", { type: "button", id: "copy-summary" }, "Copy summary");
    const exportCsv = el("button", { type: "button", id: "export-csv" }, "Export CSV");
    const reason = el("p", { class: "help", id: "export-reason" });
    if (empty) {
      copy.disabled = true; exportCsv.disabled = true;
      reason.textContent = "Nothing to copy or export: no changes were detected in this period.";
    }
    copy.addEventListener("click", async () => {
      try { await writeClipboard(data.text); notice = "Summary copied."; }
      catch { notice = "The summary could not be copied here. Select it from the export instead."; }
      showNotice(); // not draw(): that would close trials the analyst opened and clear dates they typed
    });
    exportCsv.addEventListener("click", () => download(data.filename, data.csv));
    return [el("div", { class: "outputs" }, copy, exportCsv), reason];
  }

  function draw() {
    const { counts, period: shown } = data;
    const empty = counts.field_changes === 0;
    const controls = el("div", { class: "summary-controls" }, periodButtons(), ...outputs());
    body.replaceChildren(
      el("h2", { class: "queue-title" }, "Change summary"),
      el("p", { class: "meta" }, "Changes detected in this period, whether reviewed or not."),
      controls);
    if (editing) body.append(customForm());
    if (notice) body.append(el("p", { class: "help", role: "status", id: "summary-notice" }, notice));
    body.append(
      el("h3", { class: "period-heading", id: "summary-heading" },
        `${shown.label} · ${plural(counts.trials, "trial")} · ${plural(counts.field_changes, "field change")}`),
      el("p", { class: "meta", id: "summary-counts" },
        `${counts.awaiting_review} awaiting review · ${counts.reviewed} reviewed · Dates use ${data.zone}`));
    if (empty) {
      const wider = shown.kind === "week" ? ["Show the whole month", () => choose({ kind: "month" })]
        : ["Pick other dates", () => { editing = true; draw(); }];
      const offer = el("button", { type: "button", class: "link" }, wider[0]);
      offer.addEventListener("click", () => Promise.resolve(wider[1]()).catch(showError));
      body.append(el("div", { class: "empty", id: "summary-empty" },
        el("p", {}, "No changes detected in this period."), el("p", {}, "Try a wider range: "), offer));
      return;
    }
    body.append(el("ul", { class: "queue" }, ...data.trials.map(trialCard)));
  }

  draw();
}
