import { setFooterYear, setMessage } from "./ui.js";

const escapeHtml = (s) => {
  if (s == null) return "";
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
};

const state = {
  sort: "name",
  searchQuery: "",
  allItems: [],
};

const tokenKey = "access_token";

/** Извлекает токен из hash после редиректа с логина и сохраняет в localStorage, затем убирает из URL */
function applyTokenFromHash() {
  const hash = window.location.hash || "";
  const match = /(?:^|&)access_token=([^&]+)/.exec(hash);
  if (match) {
    try {
      const token = decodeURIComponent(match[1]);
      if (token) {
        localStorage.setItem(tokenKey, token);
        const cleanHash = hash.replace(/(^|&)access_token=[^&]+/g, "").replace(/^&|&$/g, "");
        const newUrl = cleanHash ? `${window.location.pathname}${window.location.search}#${cleanHash}` : window.location.pathname + window.location.search;
        window.history.replaceState(null, "", newUrl);
      }
    } catch (e) {
      // игнорируем ошибки парсинга
    }
  }
}

const getToken = () => localStorage.getItem(tokenKey);

const setLoading = (value) => {
  const refreshButton = document.getElementById("refresh-contacts");
  if (refreshButton) {
    refreshButton.disabled = value;
  }
};

function filterContactsBySearch(items, query) {
  const q = (query || "").trim().toLowerCase();
  if (!q) return items;
  return items.filter((item) => {
    const name = (item.full_name || "").toLowerCase();
    const words = q.split(/\s+/).filter(Boolean);
    return words.every((w) => name.includes(w));
  });
}

const renderContacts = (items) => {
  const grid = document.getElementById("contacts-grid");
  const empty = document.getElementById("contacts-empty");
  if (!grid || !empty) {
    return;
  }

  const filtered = filterContactsBySearch(items, state.searchQuery);

  grid.innerHTML = "";
  if (!filtered.length) {
    empty.style.display = "block";
    empty.textContent = state.searchQuery.trim() ? "Ничего не найдено по запросу." : "Пока нет контактов.";
    return;
  }

  empty.style.display = "none";
  filtered.forEach((item) => {
    const card = document.createElement("a");
    card.className = "card contact-card contact-card-link";
    card.href = `/contact.html?id=${item.id}`;
    const lastContact = item.last_contact_at
      ? new Date(item.last_contact_at).toLocaleDateString("ru", { day: "numeric", month: "short", year: "numeric" })
      : null;
    const relType = item.relationship_type ? { business: "Деловой", personal: "Личный", other: "Другое" }[item.relationship_type] || item.relationship_type : "";
    card.innerHTML = `
      <h3>${escapeHtml(item.full_name || "Без имени")}</h3>
      ${item.projects_notes ? `<p class="muted">${escapeHtml(item.projects_notes)}</p>` : ""}
      <div class="contact-meta">
        ${item.phone ? `<span>${escapeHtml(item.phone)}</span>` : ""}
        ${item.email ? `<span>${escapeHtml(item.email)}</span>` : ""}
        ${relType ? `<span class="contact-tag">${escapeHtml(relType)}</span>` : ""}
        ${lastContact ? `<span class="muted">Контакт: ${lastContact}</span>` : ""}
      </div>
    `;
    grid.appendChild(card);
  });
};

const showAuthError = (detail) => {
  const el = document.getElementById("auth-error");
  if (el) {
    el.textContent = `Ошибка авторизации: ${detail || "401"} — через 5 сек переход на вход.`;
    el.style.display = "block";
  }
  console.error("API 401:", detail);
};

const handleUnauthorized = (response) => {
  localStorage.removeItem(tokenKey);
  response.text().then((body) => {
    let detail = body;
    try {
      const parsed = JSON.parse(body);
      if (parsed.detail) detail = parsed.detail;
    } catch (_) {}
    showAuthError(detail);
    setTimeout(() => {
      window.location.href = "/login.html";
    }, 5000);
  }).catch(() => {
    showAuthError("401");
    setTimeout(() => { window.location.href = "/login.html"; }, 5000);
  });
};

const fetchContacts = async () => {
  const token = getToken();
  if (!token) {
    window.location.href = "/login.html";
    return;
  }

  setLoading(true);
  try {
    const response = await fetch(
      `/api/v1/contacts?page=1&per_page=50&sort=${state.sort}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    if (response.status === 401) {
      handleUnauthorized(response);
      return;
    }

    if (!response.ok) {
      setMessage("contact-message", "Не удалось загрузить контакты.");
      setLoading(false);
      return;
    }

    const data = await response.json();
    state.allItems = data.items || [];
    renderContacts(state.allItems);
  } catch (error) {
    setMessage("contact-message", "Ошибка сети при загрузке контактов.");
  } finally {
    setLoading(false);
  }
};

const handleCreate = async (event) => {
  event.preventDefault();
  const token = getToken();
  if (!token) {
    window.location.href = "/login.html";
    return;
  }

  const form = event.target;
  const formData = new FormData(form);
  const payload = {
    full_name: String(formData.get("full_name") || ""),
    phone: String(formData.get("phone") || ""),
    email: String(formData.get("email") || ""),
    projects_notes: String(formData.get("projects_notes") || ""),
  };

  setMessage("contact-message", "Сохраняем...");
  try {
    const response = await fetch("/api/v1/contacts", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    if (response.status === 401) {
      handleUnauthorized(response);
      return;
    }

    if (!response.ok) {
      const errorText = await response.text();
      setMessage("contact-message", `Ошибка: ${errorText}`);
      return;
    }

    setMessage("contact-message", "Контакт добавлен.");
    form.reset();
    await fetchContacts();
  } catch (error) {
    setMessage("contact-message", "Ошибка сети. Попробуйте позже.");
  }
};

document.addEventListener("DOMContentLoaded", () => {
  setFooterYear();
  applyTokenFromHash();

  const form = document.getElementById("contact-form");
  if (form) {
    form.addEventListener("submit", handleCreate);
  }

  const refreshButton = document.getElementById("refresh-contacts");
  if (refreshButton) {
    refreshButton.addEventListener("click", fetchContacts);
  }

  const sortSelect = document.getElementById("contacts-sort");
  if (sortSelect) {
    sortSelect.addEventListener("change", (event) => {
      state.sort = event.target.value || "name";
      fetchContacts();
    });
  }

  const searchInput = document.getElementById("contacts-search");
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      state.searchQuery = searchInput.value;
      renderContacts(state.allItems);
    });
  }

  fetchContacts();
});
