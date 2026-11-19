const ROOTS = "#view, #sidebar";
const TABBABLE = 'a[href], button, input, select, textarea, summary, [tabindex]:not([tabindex="-1"])';
const WAIT_MS = 3000;

const visible = (node) => node.getClientRects().length > 0 && !node.closest("[hidden]");
const usable = (node) => node.isConnected && !node.disabled && visible(node);
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

let last = null;
let lost = null;

function settled() {
  const active = document.activeElement;
  return active && active !== document.body && !(last && active === last.node && !usable(last.node));
}

function check() {
  if (lost && Date.now() > lost.until) { lost = null; last = null; }
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
document.addEventListener("pointerdown", (event) => {
  const control = event.target.closest && event.target.closest(TABBABLE);
  lost = null;
  last = control && control.closest(ROOTS) ? describe(control) : null;
}, true);

new MutationObserver(() => {
  check();
  setTimeout(check, 60);
  setTimeout(check, 400);
}).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["disabled", "hidden", "aria-disabled"] });
