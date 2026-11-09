// Keeps the keyboard's place when a view redraws itself.
//
// Most views rebuild their DOM after an action (a page of results, a tab, a bar). The
// control that held keyboard focus is then a new node, or gone, and the browser drops
// focus to <body>: a keyboard user has to Tab in from the top again. This module
// remembers what held focus, and when focus has fallen to <body> after a redraw (the node
// was removed, replaced or disabled), puts focus on the node that replaced it. If nothing replaced it,
// on the nearest control that was beside it. It never acts after a click elsewhere, in a
// dialog, or when the address has moved to another page (a tab strip excepted: its tabs
// are the same controls on the next page).
const ROOTS = "#view, #sidebar";
const TABBABLE = 'a[href], button, input, select, textarea, summary, [tabindex]:not([tabindex="-1"])';
const WAIT_MS = 3000;

const visible = (node) => node.getClientRects().length > 0 && !node.closest("[hidden]");
const usable = (node) => node.isConnected && !node.disabled && node.getAttribute("aria-disabled") !== "true" && visible(node);
const pageOf = () => location.hash.split("?")[0];

function keyOf(node) {
  if (node.id) return `#${node.id}`;
  const href = node.tagName === "A" && node.getAttribute("href");
  if (href) return `a ${href}`;
  const own = node.getAttribute("aria-label") || (node.tagName === "INPUT" || node.tagName === "SELECT" ? "" : node.textContent.replace(/\s+/g, " ").trim());
  return [node.tagName, node.type || "", node.name || "", node.type === "checkbox" || node.type === "radio" ? node.value : "", own.slice(0, 60)].join("|");
}

function tabbables() {
  return [...document.querySelectorAll(ROOTS)].flatMap((root) => [...root.querySelectorAll(TABBABLE)]).filter(visible);
}

// The node, then its neighbours in Tab order: the ones before it nearest first, then after.
function describe(node) {
  const all = tabbables();
  const at = all.indexOf(node);
  const neighbours = at < 0 ? [] : [...all.slice(Math.max(0, at - 8), at).reverse(), ...all.slice(at + 1, at + 5)];
  const entry = (n) => {
    const key = keyOf(n);
    return { key, nth: all.filter((m) => keyOf(m) === key).indexOf(n) };
  };
  return { node, page: pageOf(), tab: node.getAttribute("role") === "tab", keys: [node, ...neighbours].map(entry) };
}

function replacement({ key, nth }) {
  const same = tabbables().filter((n) => usable(n) && keyOf(n) === key);
  return same[nth] || same[0] || null;
}

let last = null; // what held focus most recently, inside the page
let lost = null; // the same, once it has gone and focus has fallen to <body>

function settled() {
  const active = document.activeElement;
  return active && active !== document.body && !(last && active === last.node && !usable(last.node));
}

function check() {
  if (lost && Date.now() > lost.until) { lost = null; last = null; } // gave up: nothing like it came back
  if (lost && settled()) lost = null;
  if (!lost && last && !settled()) lost = { ...last, until: Date.now() + WAIT_MS };
  if (!lost) return;
  if (!lost.tab && lost.page !== pageOf()) { lost = null; last = null; return; }
  for (const entry of lost.keys) {
    const target = replacement(entry);
    if (target) { lost = null; target.focus({ preventScroll: true }); return; }
  }
}

document.addEventListener("focusin", (event) => {
  lost = null;
  last = event.target.closest && event.target.closest(ROOTS) ? describe(event.target) : null;
}, true);
// A click on something that cannot take focus is the analyst moving on, not a redraw.
// (A click on a control that already has focus fires no focusin, so it is noted here.)
document.addEventListener("pointerdown", (event) => {
  const control = event.target.closest && event.target.closest(TABBABLE);
  lost = null;
  last = control && control.closest(ROOTS) ? describe(control) : null;
}, true);

new MutationObserver(() => {
  check();
  setTimeout(check, 60); // a disabled control loses focus a moment after the change
  setTimeout(check, 400);
}).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["disabled", "hidden", "aria-disabled"] });
