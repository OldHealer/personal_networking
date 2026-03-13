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

      const rawText = await response.text();
      if (!response.ok) {
        let errorText = rawText;
        try {
          const parsed = JSON.parse(errorText);
          if (parsed.detail) {
            errorText = parsed.detail;
          }
        } catch (parseError) {
          // оставляем текст как есть, если это не JSON
        }
        setMessage(
          "login-message",
          `Ошибка (${response.status}): ${errorText || "Не удалось войти"}`
        );
        return;
      }

      let data = {};
      try {
        data = rawText ? JSON.parse(rawText) : {};
      } catch (parseError) {
        // тело не JSON
      }
      if (!data.access_token) {
        setMessage(
          "login-message",
          `Токен не получен. Ответ: ${rawText || "пустой"}`
        );
        return;
      }
      localStorage.setItem("access_token", data.access_token);
      setMessage("login-message", "Успешный вход.");
      // Редирект без токена в URL — токен уже в localStorage; так браузер не показывает длинный hash в адресной строке
      window.location.replace("/contacts.html");
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
        setMessage(
          "register-message",
          `Ошибка (${response.status}): ${errorText || "Не удалось создать аккаунт"}`
        );
        return;
      }

      try {
        await response.json();
      } catch (parseError) {
        // если тело пустое, продолжаем без падения
      }
      setMessage("register-message", "Аккаунт создан. Выполняем вход...");

      const loginResponse = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: payload.email,
          password: payload.password,
        }),
      });

      if (loginResponse.ok) {
        try {
          const loginData = await loginResponse.json();
          if (loginData.access_token) {
            localStorage.setItem("access_token", loginData.access_token);
          }
        } catch (parseError) {
          // игнорируем ошибки парсинга токена
        }
      } else {
        const loginErrorText = await loginResponse.text();
        setMessage(
          "register-message",
          `Аккаунт создан, но вход не удался (${loginResponse.status}): ${loginErrorText || "нет ответа"}`
        );
        return;
      }

      if (!localStorage.getItem("access_token")) {
        setMessage("register-message", "Аккаунт создан, но вход не удался. Попробуйте войти вручную.");
        return;
      }

      registerForm.reset();
      window.location.href = "/contacts.html";
    } catch (error) {
      setMessage("register-message", "Ошибка сети. Попробуйте позже.");
    }
  });
});
