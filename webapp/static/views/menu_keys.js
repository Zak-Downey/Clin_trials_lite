// Keyboard behaviour both ⋯ menus share: Escape closes the menu from the button or from
// inside it and leaves focus on the button; Tab out of the menu closes it, so an open
// menu never sits over the page after the keyboard has moved on.
export function menuKeys(wrap, button, close) {
  wrap.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !wrap.querySelector(".menu").hidden) {
      event.stopPropagation();
      close();
      button.focus();
    } else if (event.key === "Tab") {
      setTimeout(() => { if (!wrap.contains(document.activeElement)) close(); }, 0);
    }
  });
}
