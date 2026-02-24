import { setFooterYear, setMessage } from "./ui.js";

document.addEventListener("DOMContentLoaded", () => {
  setFooterYear();

  const form = document.getElementById("login-form");
  if (!form) {
    return;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage("login-message", "Проверяем данные...");

    const formData = new FormData(form);
    const payload = {
      username: String(formData.get("email") || ""),
      password: String(formData.get("password") || ""),
    };

    try {
      const response = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        let errorText = await response.text();
        try {
          const parsed = JSON.parse(errorText);
          if (parsed.detail) {
            errorText = parsed.detail;
          }
        } catch (parseError) {
          // оставляем текст как есть, если это не JSON
        }
        setMessage("login-message", `Ошибка: ${errorText}`);
        return;
      }

      const data = await response.json();
      if (data.access_token) {
        localStorage.setItem("access_token", data.access_token);
      }
      setMessage("login-message", "Успешный вход.");
      window.location.href = "/success.html";
    } catch (error) {
      setMessage("login-message", "Ошибка сети. Попробуйте позже.");
      window.location.href = "/error.html";
    }
  });

  const registerForm = document.getElementById("register-form");
  if (!registerForm) {
    return;
  }

  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage("register-message", "Отправляем данные...");

    const formData = new FormData(registerForm);
    const payload = {
      username: String(formData.get("username") || ""),
      first_name: String(formData.get("first_name") || ""),
      last_name: String(formData.get("last_name") || ""),
      email: String(formData.get("email") || ""),
      password: String(formData.get("password") || ""),
      tenant_name: String(formData.get("tenant_name") || ""),
    };

    try {
      const response = await fetch("/api/v1/auth/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorText = await response.text();
        setMessage("register-message", `Ошибка: ${errorText}`);
        return;
      }

      const data = await response.json();
      setMessage(
        "register-message",
        `Готово! User ID: ${data.app_user_id}`
      );
      registerForm.reset();
    } catch (error) {
      setMessage("register-message", "Ошибка сети. Попробуйте позже.");
    }
  });
});
