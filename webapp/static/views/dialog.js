// The one dialog every flow uses: focus is trapped, Escape cancels, and focus goes back
// to the control that opened it. Nothing here changes the address or the scroll position.
const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

// opener: the control that opened it; content: nodes inside; first: the node to focus first.
// Returns { close(), dialog }.
let counter = 0; // dialogs can stack (a New watchlist over Watch this search): each names itself
export function openDialog(opener, title, content, first) {
  const dialog = document.createElement("dialog");
  dialog.className = "dialog";
  const titleId = `dialog-title-${++counter}`;
  dialog.setAttribute("aria-labelledby", titleId);
  const heading = document.createElement("h2");
  heading.id = titleId;
  heading.textContent = title;
  dialog.append(heading, ...content);
  const openerId = opener && opener.id;
  dialog.addEventListener("keydown", (event) => {
    if (event.key !== "Tab") return;
    const items = [...dialog.querySelectorAll(FOCUSABLE)];
    if (!items.length) return;
    const at = items.indexOf(document.activeElement);
    if (event.shiftKey && at <= 0) { event.preventDefault(); items[items.length - 1].focus(); }
    else if (!event.shiftKey && at === items.length - 1) { event.preventDefault(); items[0].focus(); }
  });
  dialog.addEventListener("close", () => {
    dialog.remove();
    // The opener may have been redrawn meanwhile: find its replacement by id.
    const back = opener && opener.isConnected ? opener : (openerId && document.getElementById(openerId));
    // After the browser's own focus restore, which would otherwise win.
    if (back) setTimeout(() => back.focus({ preventScroll: true }), 0);
  });
  document.body.append(dialog);
  dialog.showModal();
  (first || dialog.querySelector(FOCUSABLE)).focus({ preventScroll: true });
  return { dialog, close: () => dialog.close() };
}
