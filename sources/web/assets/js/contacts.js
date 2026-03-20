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

/** Извлекает токен из hash после редиректа с логина и сохраняет в localStorage, затем убирает из URL (fallback, если strip-token-from-url.js не сработал). */
function applyTokenFromHash() {
  const hash = window.location.hash || "";
  const match = /(?:^|&)access_token=([^&]+)/.exec(hash);
  if (match) {
    try {
      const token = decodeURIComponent(match[1]);
      if (token) localStorage.setItem(tokenKey, token);
    } catch (e) {}
    // Всегда убираем токен из URL, даже если сохранение не удалось
    window.history.replaceState(null, "", window.location.pathname + window.location.search);
  }
}

const getToken = () => localStorage.getItem(tokenKey);

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
    const lastInteraction = item.last_interaction_at
      ? new Date(item.last_interaction_at).toLocaleDateString("ru", { day: "numeric", month: "short", year: "numeric" })
      : null;
    card.innerHTML = `
      <h3>${escapeHtml(item.full_name || "Без имени")}</h3>
      <div class="contact-meta">
        ${item.phone ? `<span>${escapeHtml(item.phone)}</span>` : ""}
        ${item.email ? `<span>${escapeHtml(item.email)}</span>` : ""}
        ${lastInteraction ? `<span class="contact-tag">Взаимодействие: ${escapeHtml(lastInteraction)}</span>` : `<span class="muted">Взаимодействий пока нет</span>`}
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

// --- Meeting prep agent: автодополнение контакта + вызов агента ---

let meetingContactsList = [];

function normalizeText(s) {
  return String(s || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");
}

function filterMeetingContacts(items, query) {
  const q = normalizeText(query);
  if (!q) return items;
  const words = q.split(/\s+/).filter(Boolean);
  return items.filter((c) => {
    const name = normalizeText(c.full_name);
    const email = normalizeText(c.email);
    return words.every((w) => name.includes(w) || (email && email.includes(w)));
  });
}

function showMeetingSuggestions(items, options = {}) {
  const { emptyMessage = "Введите имя или email для поиска", isRetryMessage = false } = options;
  const ul = document.getElementById("prepare-meeting-suggestions");
  const input = document.getElementById("prepare-meeting-query");
  if (!ul || !input) return;
  ul.innerHTML = "";
  ul.setAttribute("aria-hidden", "false");
  input.setAttribute("aria-expanded", "true");
  ul.classList.add("contact-suggestions-visible");

  if (!items.length) {
    const li = document.createElement("li");
    li.className = "contact-suggestions-message";
    li.setAttribute("role", "option");
    li.setAttribute("aria-disabled", "true");
    li.textContent = emptyMessage;
    if (isRetryMessage) li.dataset.retry = "1";
    ul.appendChild(li);
    return;
  }

  items.slice(0, 15).forEach((c) => {
    const li = document.createElement("li");
    li.setAttribute("role", "option");
    li.dataset.id = String(c.id || "");
    li.dataset.name = String(c.full_name || "Без имени");
    li.textContent = c.email ? `${c.full_name || "Без имени"} — ${c.email}` : (c.full_name || "Без имени");
    ul.appendChild(li);
  });
}

function hideMeetingSuggestions() {
  const ul = document.getElementById("prepare-meeting-suggestions");
  const input = document.getElementById("prepare-meeting-query");
  if (!ul) return;
  ul.innerHTML = "";
  ul.setAttribute("aria-hidden", "true");
  ul.classList.remove("contact-suggestions-visible");
  if (input) input.setAttribute("aria-expanded", "false");
}

async function fetchContactsForMeetingAutocomplete(forceRefetch = false) {
  if (!forceRefetch && meetingContactsList.length > 0) return true;
  const token = getToken();
  if (!token) {
    meetingContactsList = [];
    return false;
  }

  const perPage = 100; // API ограничивает per_page <= 100
  const maxPages = 10; // до 1000 контактов
  let success = false;

  try {
    const all = [];
    for (let page = 1; page <= maxPages; page++) {
      const response = await fetch(
        `/api/v1/contacts?page=${page}&per_page=${perPage}&sort=name`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (response.status === 401) {
        handleUnauthorized(response);
        meetingContactsList = [];
        return false;
      }
      if (!response.ok) break;

      success = true;
      const data = await response.json();
      const rawItems = Array.isArray(data.items) ? data.items : [];
      const items = rawItems.map((c) => ({
        id: c.id,
        full_name: c.full_name ?? c.fullName ?? "",
        email: c.email ?? "",
      }));
      all.push(...items);

      const total = data.total != null ? data.total : 0;
      if (items.length < perPage || all.length >= total) break;
    }

    meetingContactsList = success ? all : [];
    return success;
  } catch (e) {
    meetingContactsList = [];
    return false;
  }
}

function initPrepareMeetingAutocomplete() {
  const input = document.getElementById("prepare-meeting-query");
  const hidden = document.getElementById("prepare-meeting-contact-id");
  const ul = document.getElementById("prepare-meeting-suggestions");
  if (!input || !hidden || !ul) return;

  let hideTimeout = null;

  function clearSelectionIfTyping() {
    // если пользователь начал печатать после выбора — сбрасываем contact_id
    hidden.value = "";
  }

  input.addEventListener("focus", async () => {
    const ok = await fetchContactsForMeetingAutocomplete();
    const filtered = filterMeetingContacts(meetingContactsList, input.value);
    showMeetingSuggestions(filtered, {
      emptyMessage: ok ? "Введите имя или email для поиска" : "Не удалось загрузить список. Кликните для повторной попытки.",
      isRetryMessage: !ok,
    });
  });

  input.addEventListener("input", () => {
    clearTimeout(hideTimeout);
    clearSelectionIfTyping();
    const filtered = filterMeetingContacts(meetingContactsList, input.value);
    showMeetingSuggestions(filtered, {
      emptyMessage: meetingContactsList.length ? "Ничего не найдено" : "Загрузите список (кликните в поле)",
    });
  });

  input.addEventListener("blur", () => {
    hideTimeout = setTimeout(hideMeetingSuggestions, 150);
  });

  ul.addEventListener("mousedown", (e) => {
    e.preventDefault();
    const li = e.target.closest("li[role=option]");
    if (!li) return;

    if (li.dataset.retry === "1") {
      hideMeetingSuggestions();
      fetchContactsForMeetingAutocomplete(true).then((ok) => {
        const filtered = filterMeetingContacts(meetingContactsList, input.value);
        showMeetingSuggestions(filtered, {
          emptyMessage: ok ? "Введите имя или email для поиска" : "Не удалось загрузить список. Кликните для повторной попытки.",
          isRetryMessage: !ok,
        });
      });
      return;
    }

    if (li.classList.contains("contact-suggestions-message")) return;
    const id = String(li.dataset.id || "").trim();
    const name = String(li.dataset.name || "").trim();
    if (!id) return;
    hidden.value = id;
    input.value = name;
    hideMeetingSuggestions();
  });
}

async function prepareMeeting() {
  const input = document.getElementById("prepare-meeting-query");
  const contactIdEl = document.getElementById("prepare-meeting-contact-id");
  const messageEl = document.getElementById("prepare-meeting-message");
  const resultEl = document.getElementById("prepare-meeting-result");
  if (!input || !contactIdEl || !messageEl || !resultEl) return;

  const query = String(input.value || "").trim();
  const contact_id = String(contactIdEl.value || "").trim();

  if (!contact_id) {
    messageEl.textContent = "Выберите контакт из списка (кликните по нужному контакту в подсказках).";
    return;
  }

  const token = getToken();
  if (!token) {
    window.location.href = "/login.html";
    return;
  }

  messageEl.textContent = "Готовим рекомендации...";
  resultEl.textContent = "";

  try {
    const response = await fetch("/api/v1/agents/prepare-meeting", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ query: query || "", contact_id }),
    });

    if (response.status === 401) {
      handleUnauthorized(response);
      return;
    }

    const text = await response.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch (_) {}

    if (!response.ok) {
      const detail = data && data.detail ? data.detail : text || "Не удалось получить рекомендации.";
      messageEl.textContent = `Ошибка: ${typeof detail === "string" ? detail : JSON.stringify(detail)}`;
      return;
    }

    messageEl.textContent = `Контакт: ${data.contact_name || data.contact_id || "неизвестен"}`;
    resultEl.textContent = data.raw_markdown || "";
  } catch (e) {
    messageEl.textContent = "Сетевая ошибка при обращении к агенту.";
  }
}

const fetchContacts = async () => {
  const token = getToken();
  if (!token) {
    window.location.href = "/login.html";
    return;
  }

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
      return;
    }

    const data = await response.json();
    state.allItems = data.items || [];
    renderContacts(state.allItems);
  } catch (error) {
    setMessage("contact-message", "Ошибка сети при загрузке контактов.");
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

  const prepareForm = document.getElementById("prepare-meeting-form");
  if (prepareForm) {
    // Enter в поле запускает агента, без перезагрузки страницы
    prepareForm.addEventListener("submit", (e) => {
      e.preventDefault();
      prepareMeeting();
    });
  }
  const prepareButton = document.getElementById("prepare-meeting-button");
  if (prepareButton) {
    prepareButton.addEventListener("click", prepareMeeting);
  }
  initPrepareMeetingAutocomplete();

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
