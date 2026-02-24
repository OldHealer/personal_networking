export function setFooterYear() {
  const target = document.getElementById("footer-year");
  if (!target) {
    return;
  }
  const year = new Date().getFullYear();
  target.textContent = String(year);
}

export function setMessage(elementId, message) {
  const target = document.getElementById(elementId);
  if (!target) {
    return;
  }
  target.textContent = message;
}
