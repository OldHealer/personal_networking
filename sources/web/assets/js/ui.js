export function setFooterYear() {
  const target = document.getElementById("footer-year");
  if (!target) return;
  target.textContent = String(new Date().getFullYear());
}

export function setMessage(elementId, message) {
  const target = document.getElementById(elementId);
  if (!target) return;
  target.textContent = message;
}

export function initTheme() {
  const saved = localStorage.getItem("theme") || "light";
  document.documentElement.setAttribute("data-theme", saved);
  _updateToggleIcon(saved);
}

export function setupThemeToggle() {
  const btn = document.getElementById("theme-toggle");
  if (!btn) return;
  btn.addEventListener("click", () => {
    const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
    _updateToggleIcon(next);
  });
}

function _updateToggleIcon(theme) {
  const btn = document.getElementById("theme-toggle");
  if (btn) btn.setAttribute("aria-label", theme === "dark" ? "Светлая тема" : "Тёмная тема");
  const icon = btn?.querySelector(".theme-icon");
  if (icon) icon.textContent = theme === "dark" ? "☀️" : "🌙";
}
