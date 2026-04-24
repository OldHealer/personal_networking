import { setFooterYear, setMessage, initTheme, setupThemeToggle } from "./ui.js";

const escapeHtml = (s) => {
  if (s == null) return "";
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
};

const RELATIONSHIP_LABELS = {
  business: "Деловой", colleague: "Коллега", client: "Клиент",
  partner: "Партнёр", mentor: "Наставник", mentee: "Подопечный",
  personal: "Личный", friend: "Друг", acquaintance: "Знакомый",
  family: "Семья", other: "Другое",
};

function formatRelativeTime(dateStr) {
  const d = new Date(dateStr);
  if (isNaN(d)) return null;
  const days = Math.floor((Date.now() - d) / 86400000);
  if (days === 0) return "сегодня";
  if (days === 1) return "вчера";
  if (days < 7) return `${days} дн. назад`;
  if (days < 30) return `${Math.floor(days / 7)} нед. назад`;
  if (days < 365) return `${Math.floor(days / 30)} мес. назад`;
  return `${Math.floor(days / 365)} г. назад`;
}

const state = {
  sort: "name",
  searchQuery: "",
  staleDays: "",
  relationshipType: "",
  birthdaySoon: "",
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

const renderContacts = (items) => {
  const grid = document.getElementById("contacts-grid");
  const empty = document.getElementById("contacts-empty");
  if (!grid || !empty) {
    return;
  }

  grid.innerHTML = "";
  if (!items.length) {
    empty.style.display = "block";
    if (state.searchQuery.trim()) {
      empty.textContent = "Ничего не найдено по запросу.";
    } else if (state.staleDays) {
      empty.textContent = `Нет контактов, с которыми не общались более ${state.staleDays} дней.`;
    } else if (state.birthdaySoon) {
      empty.textContent = `Нет контактов с днём рождения в ближайшие ${state.birthdaySoon} дней.`;
    } else if (state.relationshipType) {
      empty.textContent = "Нет контактов с выбранным типом отношений.";
    } else {
      empty.textContent = "Пока нет контактов.";
    }
    return;
  }

  empty.style.display = "none";
  items.forEach((item) => {
    const card = document.createElement("a");
    card.className = "card contact-card contact-card-link";
    card.href = `/contact.html?id=${item.id}`;
    const relType = item.relationship_type || "";
    const relLabel = RELATIONSHIP_LABELS[relType] || null;
    const lastSeen = item.last_interaction_at ? formatRelativeTime(item.last_interaction_at) : null;
    card.innerHTML = `
      <div class="contact-card-header">
        <h3>${escapeHtml(item.full_name || "Без имени")}</h3>
        ${relLabel ? `<span class="contact-badge contact-badge--${escapeHtml(relType)}">${escapeHtml(relLabel)}</span>` : ""}
      </div>
      <div class="contact-meta">
        ${item.phone ? `<span>${escapeHtml(item.phone)}</span>` : ""}
        ${item.email ? `<span>${escapeHtml(item.email)}</span>` : ""}
      </div>
      <div class="contact-card-footer">
        ${lastSeen
          ? `<span class="contact-last-seen">↔ ${escapeHtml(lastSeen)}</span>`
          : `<span class="muted">Встреч не было</span>`}
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

// --- Глубокий (полнотекстовый) поиск ---

function formatOccurredAt(dateStr) {
  const d = new Date(dateStr);
  if (isNaN(d)) return "";
  return d.toLocaleString("ru-RU", { dateStyle: "medium", timeStyle: "short" });
}

// Отрисовывает snippet безопасно: экранирует всё, а <mark>…</mark> от ts_headline возвращает в разметку.
function renderSnippet(snippet) {
  if (!snippet) return "";
  const escaped = escapeHtml(snippet);
  return escaped.replace(/&lt;mark&gt;/g, "<mark>").replace(/&lt;\/mark&gt;/g, "</mark>");
}

function renderFulltextResults(data) {
  const el = document.getElementById("fulltext-results");
  if (!el) return;

  const contacts = Array.isArray(data.contacts) ? data.contacts : [];
  const interactions = Array.isArray(data.interactions) ? data.interactions : [];

  if (!contacts.length && !interactions.length) {
    el.innerHTML = `<p class="muted">Ничего не найдено.</p>`;
    return;
  }

  const parts = [];
  parts.push(`<p class="muted fulltext-summary">Найдено: ${contacts.length} контакт(ов), ${interactions.length} взаимодействие(й).</p>`);

  if (contacts.length) {
    parts.push(`<h3 class="fulltext-section-title">Контакты</h3>`);
    parts.push(`<ul class="fulltext-list">`);
    for (const c of contacts) {
      const relLabel = c.relationship_type ? (RELATIONSHIP_LABELS[c.relationship_type] || c.relationship_type) : "";
      parts.push(`
        <li class="fulltext-item">
          <a href="/contact.html?id=${encodeURIComponent(c.id)}" class="fulltext-item-link">
            <div class="fulltext-item-head">
              <span class="fulltext-item-title">${escapeHtml(c.full_name || "Без имени")}</span>
              ${relLabel ? `<span class="contact-badge contact-badge--${escapeHtml(c.relationship_type)}">${escapeHtml(relLabel)}</span>` : ""}
              ${c.email ? `<span class="muted">${escapeHtml(c.email)}</span>` : ""}
            </div>
            ${c.snippet ? `<div class="fulltext-snippet">${renderSnippet(c.snippet)}</div>` : ""}
          </a>
        </li>
      `);
    }
    parts.push(`</ul>`);
  }

  if (interactions.length) {
    parts.push(`<h3 class="fulltext-section-title">Взаимодействия</h3>`);
    parts.push(`<ul class="fulltext-list">`);
    for (const i of interactions) {
      parts.push(`
        <li class="fulltext-item">
          <a href="/contact.html?id=${encodeURIComponent(i.contact_id)}" class="fulltext-item-link">
            <div class="fulltext-item-head">
              <span class="fulltext-item-title">${escapeHtml(i.contact_full_name || "Без имени")}</span>
              ${i.channel ? `<span class="muted">${escapeHtml(i.channel)}</span>` : ""}
              <span class="muted">${escapeHtml(formatOccurredAt(i.occurred_at))}</span>
            </div>
            ${i.snippet ? `<div class="fulltext-snippet">${renderSnippet(i.snippet)}</div>` : ""}
          </a>
        </li>
      `);
    }
    parts.push(`</ul>`);
  }

  el.innerHTML = parts.join("");
}

async function performFulltextSearch(query) {
  const el = document.getElementById("fulltext-results");
  if (!el) return;
  const q = (query || "").trim();
  if (!q) {
    el.innerHTML = "";
    return;
  }

  const token = getToken();
  if (!token) {
    window.location.href = "/login.html";
    return;
  }

  el.innerHTML = `<p class="muted">Ищем…</p>`;
  try {
    const params = new URLSearchParams({ q, limit: "30" });
    const response = await fetch(`/api/v1/search?${params}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (response.status === 401) {
      handleUnauthorized(response);
      return;
    }
    if (!response.ok) {
      el.innerHTML = `<p class="form-message">Ошибка поиска: ${response.status}</p>`;
      return;
    }
    const data = await response.json();
    renderFulltextResults(data);
  } catch (e) {
    el.innerHTML = `<p class="form-message">Ошибка сети при поиске.</p>`;
  }
}

const fetchContacts = async () => {
  const token = getToken();
  if (!token) {
    window.location.href = "/login.html";
    return;
  }

  const params = new URLSearchParams({ page: 1, per_page: 50, sort: state.sort });
  if (state.searchQuery.trim()) params.set("q", state.searchQuery.trim());
  if (state.staleDays) params.set("last_contact_before", state.staleDays);
  if (state.relationshipType) params.set("relationship_type", state.relationshipType);
  if (state.birthdaySoon) params.set("has_birthday_soon", state.birthdaySoon);

  try {
    const response = await fetch(`/api/v1/contacts?${params}`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (response.status === 401) {
      handleUnauthorized(response);
      return;
    }

    if (!response.ok) {
      setMessage("contact-message", "Не удалось загрузить контакты.");
      return;
    }

    const data = await response.json();
    renderContacts(data.items || []);
  } catch (error) {
    setMessage("contact-message", "Ошибка сети при загрузке контактов.");
  }
};

// --- Сайдбар: статистика, дни рождения, давно не общались ---

const RELATIONSHIP_LABELS_STATS = {
  business: "Деловые", colleague: "Коллеги", client: "Клиенты",
  partner: "Партнёры", mentor: "Наставники", mentee: "Подопечные",
  personal: "Личные", friend: "Друзья", acquaintance: "Знакомые",
  family: "Семья", other: "Другие",
};

function renderSidebarStats(data) {
  const el = document.getElementById("sidebar-stats");
  if (!el) return;
  const total = data.total || 0;
  const byType = data.by_type || {};

  const sorted = Object.entries(byType)
    .filter(([, cnt]) => cnt > 0)
    .sort((a, b) => b[1] - a[1]);

  const rows = sorted.map(([type, cnt]) => {
    const label = RELATIONSHIP_LABELS_STATS[type] || type;
    const pct = total ? Math.round((cnt / total) * 100) : 0;
    return `<div class="stats-row">
      <span class="stats-label">${escapeHtml(label)}</span>
      <span class="stats-bar-wrap"><span class="stats-bar" style="width:${pct}%"></span></span>
      <span class="stats-count">${cnt}</span>
    </div>`;
  }).join("");

  el.innerHTML = `
    <div class="stats-total">Всего: <strong>${total}</strong></div>
    <div class="stats-list">${rows}</div>`;
}

async function fetchStats() {
  const token = getToken();
  if (!token) return;
  try {
    const res = await fetch("/api/v1/contacts/stats", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      renderSidebarStats(await res.json());
    } else {
      const el = document.getElementById("sidebar-stats");
      if (el) el.innerHTML = "";
    }
  } catch (_) {
    const el = document.getElementById("sidebar-stats");
    if (el) el.innerHTML = "";
  }
}

function daysUntilBirthday(birthdayStr) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const bday = new Date(birthdayStr + "T00:00:00");
  const next = new Date(today.getFullYear(), bday.getMonth(), bday.getDate());
  if (next < today) next.setFullYear(today.getFullYear() + 1);
  return Math.round((next - today) / 86400000);
}

function formatBirthdayDate(birthdayStr) {
  const d = new Date(birthdayStr + "T00:00:00");
  return d.toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
}

function renderSidebarBirthdays(items) {
  const el = document.getElementById("sidebar-birthdays");
  if (!el) return;
  if (!items.length) {
    el.innerHTML = `<p class="muted sidebar-empty">Нет дней рождения в ближайшие 90 дней</p>`;
    return;
  }
  el.innerHTML = items.map((c) => {
    const days = daysUntilBirthday(c.birthday);
    const dateStr = formatBirthdayDate(c.birthday);
    const daysLabel = days === 0 ? "сегодня" : days === 1 ? "завтра" : `через ${days} дн.`;
    return `<a href="/contact.html?id=${encodeURIComponent(c.id)}" class="sidebar-contact-item">
      <span class="sidebar-contact-name">${escapeHtml(c.full_name || "Без имени")}</span>
      <span class="sidebar-contact-meta">${dateStr} — ${daysLabel}</span>
    </a>`;
  }).join("");
}

function renderSidebarStale(items) {
  const el = document.getElementById("sidebar-stale");
  if (!el) return;
  if (!items.length) {
    el.innerHTML = `<p class="muted sidebar-empty">Все контакты в порядке</p>`;
    return;
  }
  el.innerHTML = items.map((c) => {
    const meta = c.last_interaction_at
      ? `${formatRelativeTime(c.last_interaction_at)}`
      : "не общались никогда";
    return `<a href="/contact.html?id=${encodeURIComponent(c.id)}" class="sidebar-contact-item">
      <span class="sidebar-contact-name">${escapeHtml(c.full_name || "Без имени")}</span>
      <span class="sidebar-contact-meta">${meta}</span>
    </a>`;
  }).join("");
}

async function fetchSidebar() {
  const token = getToken();
  if (!token) return;
  const headers = { Authorization: `Bearer ${token}` };

  const birthdaysTask = (async () => {
    try {
      const res = await fetch("/api/v1/contacts?has_birthday_soon=90&per_page=20&sort=name", { headers });
      if (!res.ok) throw new Error("birthdays fetch failed");
      const data = await res.json();
      const sorted = (data.items || [])
        .filter((c) => c.birthday)
        .map((c) => ({ ...c, _days: daysUntilBirthday(c.birthday) }))
        .sort((a, b) => a._days - b._days)
        .slice(0, 3);
      renderSidebarBirthdays(sorted);
    } catch (_) {
      const el = document.getElementById("sidebar-birthdays");
      if (el) el.innerHTML = `<p class="muted sidebar-empty">Не удалось загрузить</p>`;
    }
  })();

  const staleTask = (async () => {
    try {
      const res = await fetch("/api/v1/contacts?last_contact_before=45&per_page=15&sort=name", { headers });
      if (!res.ok) throw new Error("stale fetch failed");
      const data = await res.json();
      const items = data.items || [];
      for (let i = items.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [items[i], items[j]] = [items[j], items[i]];
      }
      renderSidebarStale(items.slice(0, 3));
    } catch (_) {
      const el = document.getElementById("sidebar-stale");
      if (el) el.innerHTML = `<p class="muted sidebar-empty">Не удалось загрузить</p>`;
    }
  })();

  await Promise.all([birthdaysTask, staleTask]);
}

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
  initTheme();
  setupThemeToggle();
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

  const staleSelect = document.getElementById("contacts-stale");
  if (staleSelect) {
    staleSelect.addEventListener("change", (event) => {
      state.staleDays = event.target.value || "";
      fetchContacts();
    });
  }

  const relSelect = document.getElementById("contacts-relationship");
  if (relSelect) {
    relSelect.addEventListener("change", (event) => {
      state.relationshipType = event.target.value || "";
      fetchContacts();
    });
  }

  const bdaySelect = document.getElementById("contacts-birthday");
  if (bdaySelect) {
    bdaySelect.addEventListener("change", (event) => {
      state.birthdaySoon = event.target.value || "";
      fetchContacts();
    });
  }

  const searchInput = document.getElementById("contacts-search");
  if (searchInput) {
    let searchDebounce = null;
    searchInput.addEventListener("input", () => {
      state.searchQuery = searchInput.value;
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(fetchContacts, 300);
    });
  }

  const fulltextForm = document.getElementById("fulltext-form");
  const fulltextQuery = document.getElementById("fulltext-query");
  if (fulltextForm && fulltextQuery) {
    fulltextForm.addEventListener("submit", (e) => {
      e.preventDefault();
      performFulltextSearch(fulltextQuery.value);
    });
    let ftDebounce = null;
    fulltextQuery.addEventListener("input", () => {
      clearTimeout(ftDebounce);
      ftDebounce = setTimeout(() => performFulltextSearch(fulltextQuery.value), 400);
    });
  }

  // Переключатель режимов поиска
  document.querySelectorAll(".search-mode-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const mode = btn.dataset.mode;
      document.querySelectorAll(".search-mode-btn").forEach((b) => {
        const active = b === btn;
        b.classList.toggle("is-active", active);
        b.setAttribute("aria-selected", active ? "true" : "false");
      });

      const namePanel = document.getElementById("search-mode-name");
      const fulltextPanel = document.getElementById("search-mode-fulltext");

      if (mode === "name") {
        namePanel.hidden = false;
        fulltextPanel.hidden = true;
        // Сбрасываем fulltext-результаты
        const results = document.getElementById("fulltext-results");
        if (results) results.innerHTML = "";
        if (fulltextQuery) fulltextQuery.value = "";
        if (searchInput) searchInput.focus();
      } else {
        namePanel.hidden = true;
        fulltextPanel.hidden = false;
        // Сбрасываем фильтр по имени
        if (searchInput) searchInput.value = "";
        state.searchQuery = "";
        fetchContacts();
        if (fulltextQuery) fulltextQuery.focus();
      }
    });
  });

  fetchContacts();
  fetchSidebar();
  fetchStats();
});
