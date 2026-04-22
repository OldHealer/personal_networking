import { setFooterYear, initTheme, setupThemeToggle, showToast } from "./ui.js";

const FIELD_LABELS = {
  password: "Пароль",
  email: "Email",
  username: "Имя пользователя",
  first_name: "Имя",
  last_name: "Фамилия",
  tenant_name: "Название организации",
};

function parseErrorMessage(status, data, rawText) {
  if (status === 422 && data && Array.isArray(data.detail)) {
    return data.detail.map((err) => {
      const field = err.loc?.[err.loc.length - 1] || "";
      const label = FIELD_LABELS[field] || field;
      const msg = err.msg || "ошибка";
      if (err.type === "string_too_short") {
        const min = err.ctx?.min_length;
        return `${label}: слишком короткое${min ? ` (минимум ${min} символов)` : ""}`;
      }
      if (err.type === "missing") return `${label}: обязательное поле`;
      if (err.type === "value_error") return `${label}: неверное значение`;
      return `${label}: ${msg}`;
    }).join(" · ");
  }
  if (data?.detail) {
    return typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
  }
  return rawText || `Ошибка ${status}`;
}

function initTabs() {
  const tabs = document.querySelectorAll(".auth-tab");
  const panels = document.querySelectorAll(".auth-tab-panel");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("auth-tab--active"));
      tab.classList.add("auth-tab--active");
      const target = tab.dataset.tab;
      panels.forEach((p) => { p.hidden = p.dataset.panel !== target; });
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  setupThemeToggle();
  setFooterYear();
  initTabs();

  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(loginForm);
      const payload = {
        username: String(fd.get("email") || ""),
        password: String(fd.get("password") || ""),
      };
      try {
        const response = await fetch("/api/v1/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const rawText = await response.text();
        let data = null;
        try { data = rawText ? JSON.parse(rawText) : null; } catch (_) {}
        if (!response.ok) {
          showToast(parseErrorMessage(response.status, data, rawText));
          return;
        }
        if (!data?.access_token) {
          showToast("Токен не получен. Попробуйте ещё раз.");
          return;
        }
        localStorage.setItem("access_token", data.access_token);
        window.location.replace("/contacts.html");
      } catch (_) {
        showToast("Ошибка сети. Проверьте подключение.");
      }
    });
  }

  const registerForm = document.getElementById("register-form");
  if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(registerForm);
      const payload = {
        username: String(fd.get("username") || ""),
        first_name: String(fd.get("first_name") || ""),
        last_name: String(fd.get("last_name") || ""),
        email: String(fd.get("email") || ""),
        password: String(fd.get("password") || ""),
        tenant_name: String(fd.get("tenant_name") || ""),
      };
      try {
        const response = await fetch("/api/v1/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!response.ok) {
          const rawText = await response.text();
          let data = null;
          try { data = rawText ? JSON.parse(rawText) : null; } catch (_) {}
          showToast(parseErrorMessage(response.status, data, rawText));
          return;
        }
        try { await response.json(); } catch (_) {}

        const loginResp = await fetch("/api/v1/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: payload.email, password: payload.password }),
        });
        if (loginResp.ok) {
          try {
            const loginData = await loginResp.json();
            if (loginData.access_token) localStorage.setItem("access_token", loginData.access_token);
          } catch (_) {}
        } else {
          showToast("Аккаунт создан, но войти не удалось. Войдите вручную.", "info");
          return;
        }
        if (!localStorage.getItem("access_token")) {
          showToast("Аккаунт создан. Войдите вручную.", "info");
          return;
        }
        registerForm.reset();
        window.location.href = "/contacts.html";
      } catch (_) {
        showToast("Ошибка сети. Проверьте подключение.");
      }
    });
  }
});
