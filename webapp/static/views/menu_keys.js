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
