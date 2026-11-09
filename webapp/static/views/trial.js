import { get, post, when } from "/static/api.js";
import { menuKeys } from "/static/views/menu_keys.js";

const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const kid of kids) node.append(kid);
  return node;
};
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

// The trial page: header, tabs, and the Changes tab with its review action bar.
export async function render(root, nct, tab, origin) {
  const trial = await get(`/api/trials/${nct}`);
  // The list the analyst came from, else the first watchlist holding the trial.
  const home = trial.watchlists.find((w) => origin && w.id === origin.listId) || trial.watchlists[0];
  const others = trial.watchlists.filter((w) => !home || w.id !== home.id);
  const state = { reviewed: false, event: null };

  const back = el("a", { class: "back", "data-back": "", href: home ? `#/watchlists/${home.id}/${origin && origin.listId === home.id && origin.tab || "needs-review"}` : "#/watchlists" },
    `‹ Back to ${home ? home.name : "watchlists"}`);
  const meta = el("p", { class: "meta" }, [nct, trial.last_checked ? `Last checked ${when(trial.last_checked)}` : "Not yet checked"].join(" · "));
  if (trial.check_failed) {
    meta.append(" ", el("span", { class: "warning", role: "note" },
      `⚠ Latest check failed${trial.check_failed.at ? ` (${when(trial.check_failed.at)})` : ""}`));
  }
  const menuButton = el("button", { type: "button", class: "secondary menu-button", "aria-label": "More actions", "aria-haspopup": "menu", "aria-expanded": "false" }, "⋯");
  const menu = el("div", { class: "menu", role: "menu", "aria-label": "Trial actions", hidden: "" });
  const menuWrap = el("div", { class: "menu-wrap" }, menuButton, menu);
  const title = el("div", { class: "trial-head" },
    el("div", {}, el("h1", {}, trial.heading), meta),
    el("div", { class: "head-actions" },
      el("a", { class: "source", href: trial.registry_url, target: "_blank", rel: "noopener" }, "Open ClinicalTrials.gov ↗"),
      menuWrap));
  const banner = el("div", { class: "banner", role: "status", hidden: "" });
  const count = el("span", { class: "tab-count" });
  const changesTab = el("a", { role: "tab", "aria-selected": String(tab === "changes"), href: `#/trials/${nct}` }, "Changes ", count);
  const tabs = el("nav", { class: "tabs", role: "tablist", "aria-label": "Trial" }, changesTab,
    el("a", { role: "tab", "aria-selected": String(tab === "details"), href: `#/trials/${nct}/details` }, "Trial details"),
    el("a", { role: "tab", "aria-selected": String(tab === "history"), href: `#/trials/${nct}/history` }, "History"));
  const body = el("div", { class: "trial-body" });
  root.replaceChildren(back, title, banner, tabs, body);

  const shown = trial.groups.flatMap((g) => g.changes);
  const ids = shown.flatMap((c) => c.ids);
  const setCount = () => { count.textContent = !state.reviewed && shown.length ? String(shown.length) : ""; };
  setCount();

  const tell = (text, undo) => {
    banner.hidden = false;
    banner.className = "banner";
    banner.replaceChildren(el("span", {}, text));
    if (undo) banner.append(undo);
  };
  const fail = (err) => { banner.hidden = false; banner.className = "banner error-banner"; banner.textContent = err.message; };

  // The menu: which watchlists hold the trial, and Remove from this list (this one only).
  const drawMenu = () => {
    menu.replaceChildren(el("p", { class: "menu-title" }, "In watchlists"),
      ...(trial.watchlists.length
        ? trial.watchlists.map((w) => el("p", { class: "menu-list", role: "presentation" }, w.name))
        : [el("p", { class: "menu-list", role: "presentation" }, "None: not being monitored")]));
    if (home && trial.watchlists.some((w) => w.id === home.id)) {
      const remove = el("button", { type: "button", role: "menuitem", class: "menu-item" }, "Remove from this list");
      remove.addEventListener("click", async () => {
        closeMenu();
        try {
          const done = await post(`/api/watchlists/${home.id}/trials/${nct}/remove`);
          trial.watchlists = done.watchlists;
          drawMenu();
          const undo = el("button", { type: "button", class: "link" }, "Undo");
          undo.addEventListener("click", async () => {
            try {
              const back = await post("/api/removals/undo", { token: done.undo });
              trial.watchlists = back.watchlists;
              drawMenu();
              banner.hidden = true;
              window.dispatchEvent(new Event("reviewchange"));
            } catch (err) { fail(err); }
          });
          tell(`Removed from ${home.name}.${done.watchlists.length ? "" : " Its history is kept."}`, undo);
          window.dispatchEvent(new Event("reviewchange"));
        } catch (err) { fail(err); }
      });
      menu.append(remove);
    }
  };
  const closeMenu = () => { menu.hidden = true; menuButton.setAttribute("aria-expanded", "false"); };
  menuButton.addEventListener("click", (event) => {
    event.stopPropagation();
    menu.hidden = !menu.hidden;
    menuButton.setAttribute("aria-expanded", String(!menu.hidden));
  });
  document.addEventListener("click", (event) => { if (!menu.contains(event.target)) closeMenu(); });
  menuKeys(menuWrap, menuButton, closeMenu);
  drawMenu();

  if (tab === "details") { await drawDetails(body, nct); return; }
  if (tab === "history") { await drawHistory(body, nct); return; }

  const heading = el("h2", {});
  const list = el("div", { class: "change-list" });
  const cards = [];
  for (const group of trial.groups) {
    const dates = [group.registry_updated ? `Registry updated ${group.registry_updated}` : null,
      `Detected ${when(group.detected_at)}`].filter(Boolean).join(" · ");
    const section = el("section", { class: "check-group" }, el("p", { class: "meta group-dates" }, dates));
    for (const change of group.changes) {
      const word = (q) => (q ? ` · ${q}` : "");
      // A long value gets the whole width: Previously above Now, rather than side by side.
      const long = [change.previous, change.current].some((v) => v.length > 80 || v.includes("\n"));
      const card = el("article", { class: long ? "change long" : "change" },
        el("h3", { class: "field-name" }, change.label),
        el("div", { class: "value previously" }, el("span", { class: "tag" }, "Previously"), el("p", {}, change.previous + word(change.previous_qualifier))),
        el("div", { class: "value now" }, el("span", { class: "tag" }, "Now"), el("p", {}, change.current + word(change.qualifier))));
      const label = el("span", { class: "reviewed-label", hidden: "" }, "Reviewed");
      card.prepend(label);
      cards.push(label);
      section.append(card);
    }
    list.append(section);
  }
  const headline = el("div", { class: "changes-head" }, heading);
  if (trial.simulated) headline.append(el("span", { class: "simulated-label" }, "Simulated changes"));
  body.append(headline);
  if (!shown.length) {
    heading.textContent = "No unreviewed changes";
    body.append(el("p", { class: "meta" }, "Everything detected on this trial has been reviewed. History keeps the record."));
    return;
  }
  body.append(list);

  const scope = el("strong", {});
  // The scope is always stated in full; a long list scrolls inside a small box (the box takes the keyboard when it overflows).
  const also = el("span", { class: "meta also" },
    others.length ? `Also clears these changes in: ${others.map((w) => w.name).join(", ")}.`
      : "No other watchlist holds this trial.");
  if (others.length > 3) { also.setAttribute("tabindex", "0"); also.setAttribute("role", "group"); also.setAttribute("aria-label", "Other watchlists this review also applies to"); }
  const next = el("button", { type: "button", class: "secondary" }, "Next trial");
  const mark = el("button", { type: "button", class: "primary" }, "Mark reviewed");
  const bar = el("div", { class: "action-bar", role: "region", "aria-label": "Review" },
    el("div", {}, scope, el("br"), also), el("div", { class: "buttons" }, next, mark));
  body.append(bar);

  const draw = () => {
    heading.textContent = state.reviewed ? `${plural(shown.length, "change")} reviewed` : `${plural(shown.length, "unreviewed change")}`;
    scope.textContent = state.reviewed ? `These ${shown.length} changes are reviewed.` : `Review covers all ${shown.length} changes shown above.`;
    cards.forEach((label) => { label.hidden = !state.reviewed; });
    mark.disabled = state.reviewed;
    setCount();
  };
  const refresh = () => window.dispatchEvent(new Event("reviewchange"));

  mark.addEventListener("click", async () => {
    try {
      const done = await post(`/api/trials/${nct}/review`, { ids });
      state.reviewed = true;
      state.event = done.event;
      draw();
      const undo = el("button", { type: "button", class: "link" }, "Undo");
      undo.addEventListener("click", async () => {
        try {
          await post(`/api/reviews/${done.event.id}/undo`);
          state.reviewed = false;
          state.event = null;
          draw();
          banner.hidden = true;
          refresh();
          mark.focus({ preventScroll: true }); // the Undo just pressed is gone: keep the keyboard in place
        } catch (err) { fail(err); }
      });
      tell(`${plural(shown.length, "change")} marked reviewed. This trial stays open.`, undo);
      undo.focus({ preventScroll: true }); // the pressed button is now disabled: focus must not fall to <body>
      refresh();
    } catch (err) { fail(err); }
  });

  // The queue as it stood when the page opened: Next trial goes to the one after this.
  let order = [];
  if (home) {
    try { order = (await get(`/api/watchlists/${home.id}/needs-review`)).trials.map((t) => t.nct_id); } catch { order = []; }
  }
  const at = order.indexOf(nct);
  const following = at >= 0 ? order[at + 1] : order.find((n) => n !== nct);
  if (following) next.addEventListener("click", () => { location.hash = `#/trials/${following}`; });
  else { next.disabled = true; next.title = "No other trial needs review"; }
  draw();
}

const field = (f) => {
  const value = f.items
    ? el("ul", { class: "value-list" }, ...f.items.map((i) => el("li", {}, i)))
    : el("p", { class: f.reported ? "field-value" : "field-value not-reported" }, f.value);
  const row = el("div", { class: "detail-field" }, el("dt", {}, f.label), el("dd", {}, value));
  if (f.changed) row.append(el("span", { class: "unreviewed-flag" }, "Unreviewed change"));
  return row;
};

// Trial details: At a glance, and five sections, long ones expandable on demand.
async function drawDetails(body, nct) {
  drawSections(body, await get(`/api/trials/${nct}/details`));
}

// The same sections for a trial not monitored (no monitoring_began, nothing unreviewed).
export function drawSections(body, details) {
  const glance = el("aside", { class: "glance", "aria-label": "At a glance" }, el("h2", {}, "At a glance"));
  const facts = el("dl", {});
  const names = { overallStatus: "Registry status", phases: "Phase", leadSponsor: "Lead sponsor", enrollment: "Enrolment" };
  for (const f of details.glance) facts.append(el("div", { class: "fact" }, el("dt", {}, names[f.field] || f.label), el("dd", { class: f.reported ? "" : "not-reported" }, f.value, ...(f.changed ? [" ", el("span", { class: "unreviewed-flag" }, "Unreviewed change")] : []))));
  facts.append(el("div", { class: "fact" }, el("dt", {}, "ClinicalTrials.gov"),
    el("dd", {}, el("a", { href: details.registry_url, target: "_blank", rel: "noopener" }, "Open the registry record ↗"))));
  if (details.monitoring_began) facts.append(el("div", { class: "fact" }, el("dt", {}, "Monitoring began"), el("dd", {}, details.monitoring_began)));
  glance.append(facts);
  const sections = el("div", { class: "detail-sections" });
  details.sections.forEach((section, index) => {
    const panel = el("dl", { class: "section-body" }, ...section.fields.map(field));
    const wrap = el("section", { class: "detail-section" });
    if (section.locked_open) {
      // A section holding an unreviewed change is never collapsed.
      wrap.append(el("h2", {}, section.title, " ", el("span", { class: "unreviewed-flag" }, `${section.unreviewed} unreviewed`)), panel);
    } else {
      const open = index === 0;
      const toggle = el("button", { type: "button", class: "section-toggle", "aria-expanded": String(open) }, el("span", {}, section.title), el("span", { class: "plus", "aria-hidden": "true" }, open ? "−" : "+"));
      panel.hidden = !open;
      toggle.addEventListener("click", () => {
        panel.hidden = !panel.hidden;
        toggle.setAttribute("aria-expanded", String(!panel.hidden));
        toggle.lastChild.textContent = panel.hidden ? "+" : "−";
      });
      wrap.append(el("h2", {}, toggle), panel);
    }
    sections.append(wrap);
  });
  body.append(el("div", { class: "details-layout" }, glance, sections));
}

const clock = (time) => {
  const m = time && /T(\d\d:\d\d)/.exec(time.iso);
  return m ? m[1] : "";
};

// History: one newest-first timeline.
async function drawHistory(body, nct) {
  const { entries } = await get(`/api/trials/${nct}/history`);
  const list = el("ol", { class: "timeline" });
  for (const e of entries) {
    const item = el("li", { class: `entry ${e.kind}` });
    const text = el("div", { class: "entry-text" });
    let tag = "";
    if (e.kind === "detection") {
      tag = plural(e.count, "change");
      text.append(el("strong", {}, `Detected ${when(e.at)}`), el("p", {}, e.fields.join(" · ")));
      const detail = el("ul", { class: "transitions", hidden: "" }, ...e.moves.map((m) => el("li", {},
        el("strong", {}, m.label), ` ${m.previous}${m.previous_qualifier ? ` · ${m.previous_qualifier}` : ""} → ${m.current}${m.qualifier ? ` · ${m.qualifier}` : ""}`,
        m.reviewed ? el("span", { class: "reviewed-tag" }, " Reviewed") : "")));
      const toggle = el("button", { type: "button", class: "link", "aria-expanded": "false" }, "Show details");
      toggle.addEventListener("click", () => {
        detail.hidden = !detail.hidden;
        toggle.setAttribute("aria-expanded", String(!detail.hidden));
        toggle.textContent = detail.hidden ? "Show details" : "Hide details";
      });
      text.append(toggle, detail);
    } else if (e.kind === "review" || e.kind === "undo") {
      const from = e.from_checks.length === 1 ? `the ${clock(e.from_checks[0])} check` : `${e.from_checks.length} checks`;
      tag = e.kind === "review" ? "Reviewed" : "Undone";
      const sentence = e.kind === "review" ? `Marked ${plural(e.count, "change")} from ${from} as reviewed`
        : `Undid the review of ${plural(e.count, "change")} from ${from}`;
      text.append(el("strong", {}, when(e.at)), el("p", {}, sentence));
    } else {
      const words = { start: "Monitoring started", stopped: "Stopped monitoring", resumed: "Resumed monitoring" };
      tag = e.kind === "start" ? "Monitoring" : "Not monitored";
      text.append(el("strong", {}, when(e.at)), el("p", {}, words[e.kind]));
      if (e.kind === "stopped") text.append(el("p", { class: "meta" }, "No check looked at this trial until monitoring resumed."));
    }
    item.append(el("span", { class: "entry-tag" }, tag), text);
    list.append(item);
  }
  body.append(el("h2", {}, "Trial history"), el("p", { class: "meta" }, "All monitored fields in one timeline · Newest first"), list);
}
