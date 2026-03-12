import { setFooterYear, setMessage } from "./ui.js";

const tokenKey = "access_token";

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
    } catch (e) {}
  }
}

const getToken = () => localStorage.getItem(tokenKey);

function getContactId() {
  const params = new URLSearchParams(window.location.search);
  return params.get("id");
}

function apiHeaders() {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${getToken()}`,
  };
}

function showAuthError(detail) {
  const el = document.getElementById("auth-error");
  if (el) {
    el.textContent = `Ошибка авторизации: ${detail || "401"}.`;
    el.style.display = "block";
  }
}

function handleUnauthorized(response) {
  localStorage.removeItem(tokenKey);
  response.text().then((body) => {
    let detail = body;
    try {
      const parsed = JSON.parse(body);
      if (parsed.detail) detail = parsed.detail;
    } catch (_) {}
    showAuthError(detail);
    setTimeout(() => { window.location.href = "/login.html"; }, 3000);
  }).catch(() => {
    showAuthError("401");
    setTimeout(() => { window.location.href = "/login.html"; }, 3000);
  });
}

function toDatetimeLocal(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const h = String(d.getHours()).padStart(2, "0");
  const min = String(d.getMinutes()).padStart(2, "0");
  return `${y}-${m}-${day}T${h}:${min}`;
}

function toDateOnly(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toISOString().slice(0, 10);
}

function fromFormData(form) {
  const fd = new FormData(form);
  const listFields = ["hobbies", "interests", "goals", "promises"];
  const payload = {};
  for (const [key, value] of fd.entries()) {
    if (listFields.includes(key)) {
      const lines = String(value || "").split("\n").map((s) => s.trim()).filter(Boolean);
      payload[key] = lines;
    } else if (key === "socials") {
      const raw = String(value || "").trim();
      if (!raw) {
        payload[key] = {};
      } else {
        try {
          payload[key] = JSON.parse(raw);
        } catch (_) {
          payload[key] = {};
        }
      }
    } else if (key === "competence_rating") {
      const n = parseInt(value, 10);
      payload[key] = Number.isNaN(n) || value === "" ? null : n;
    } else if (key === "first_met_at" || key === "last_contact_at") {
      payload[key] = value ? new Date(value).toISOString() : null;
    } else if (key === "birthday") {
      payload[key] = value || null;
    } else {
      payload[key] = value === "" ? null : value;
    }
  }
  return payload;
}

function contactToFormValues(c) {
  const listToText = (arr) => (Array.isArray(arr) && arr.length ? arr.join("\n") : "");
  return {
    full_name: c.full_name ?? "",
    phone: c.phone ?? "",
    email: c.email ?? "",
    address: c.address ?? "",
    relationship_type: c.relationship_type ?? "",
    first_met_at: toDatetimeLocal(c.first_met_at),
    first_met_place: c.first_met_place ?? "",
    first_met_context: c.first_met_context ?? "",
    projects_notes: c.projects_notes ?? "",
    family_status: c.family_status ?? "",
    birthday: toDateOnly(c.birthday),
    hobbies: listToText(c.hobbies),
    interests: listToText(c.interests),
    last_contact_at: toDatetimeLocal(c.last_contact_at),
    last_contact_summary: c.last_contact_summary ?? "",
    competence_rating: c.competence_rating ?? "",
    competence_notes: c.competence_notes ?? "",
    recommendations: c.recommendations ?? "",
    promises: listToText(c.promises),
    goals: listToText(c.goals),
    ambitions: c.ambitions ?? "",
    socials: typeof c.socials === "object" && c.socials !== null ? JSON.stringify(c.socials, null, 2) : "{}",
  };
}

function fillForm(form, values) {
  for (const [name, value] of Object.entries(values)) {
    const el = form.elements[name];
    if (el) el.value = value ?? "";
  }
}

function setFormReadonly(form, readonly) {
  for (const el of form.querySelectorAll("input, select, textarea")) {
    el.readOnly = readonly;
    el.disabled = readonly;
  }
}

function setViewMode(form, contact) {
  setFormReadonly(form, true);
  document.getElementById("btn-edit").style.display = "";
  document.getElementById("btn-save").style.display = "none";
  document.getElementById("btn-cancel").style.display = "none";
  document.getElementById("btn-delete").style.display = "";
  if (contact) {
    document.getElementById("contact-title").textContent = contact.full_name || "Контакт";
    const created = contact.created_at ? new Date(contact.created_at).toLocaleString("ru") : "";
    const updated = contact.updated_at ? new Date(contact.updated_at).toLocaleString("ru") : "";
    document.getElementById("meta-created").textContent = `Создан: ${created}`;
    document.getElementById("meta-updated").textContent = `Обновлён: ${updated}`;
  }
}

function setEditMode(form) {
  setFormReadonly(form, false);
  document.getElementById("btn-edit").style.display = "none";
  document.getElementById("btn-save").style.display = "";
  document.getElementById("btn-cancel").style.display = "";
  document.getElementById("btn-delete").style.display = "none";
}

let currentContact = null;

async function fetchContact(id) {
  const token = getToken();
  if (!token) {
    window.location.href = "/login.html";
    return null;
  }
  const response = await fetch(`/api/v1/contacts/${id}`, { headers: { Authorization: `Bearer ${token}` } });
  if (response.status === 401) {
    handleUnauthorized(response);
    return null;
  }
  if (!response.ok) {
    setMessage("contact-page-message", "Не удалось загрузить контакт.");
    return null;
  }
  return response.json();
}

async function loadContact() {
  const id = getContactId();
  if (!id) {
    window.location.href = "/contacts.html";
    return;
  }
  document.getElementById("contact-loading").style.display = "block";
  document.getElementById("contact-content").style.display = "none";
  const contact = await fetchContact(id);
  document.getElementById("contact-loading").style.display = "none";
  if (!contact) return;
  currentContact = contact;
  const form = document.getElementById("contact-form");
  fillForm(form, contactToFormValues(contact));
  setViewMode(form, contact);
  document.getElementById("contact-content").style.display = "block";
}

async function saveContact() {
  const id = getContactId();
  if (!id || !currentContact) return;
  const form = document.getElementById("contact-form");
  const payload = fromFormData(form);
  setMessage("contact-page-message", "Сохранение...");
  const response = await fetch(`/api/v1/contacts/${id}`, {
    method: "PATCH",
    headers: apiHeaders(),
    body: JSON.stringify(payload),
  });
  if (response.status === 401) {
    handleUnauthorized(response);
    return;
  }
  if (!response.ok) {
    const text = await response.text();
    setMessage("contact-page-message", `Ошибка: ${text}`);
    return;
  }
  const updated = await response.json();
  currentContact = updated;
  fillForm(form, contactToFormValues(updated));
  setViewMode(form, updated);
  setMessage("contact-page-message", "Сохранено.");
  setTimeout(() => setMessage("contact-page-message", ""), 2000);
}

async function deleteContact() {
  const id = getContactId();
  if (!id || !confirm("Удалить этот контакт?")) return;
  const response = await fetch(`/api/v1/contacts/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (response.status === 401) {
    handleUnauthorized(response);
    return;
  }
  if (response.status === 204 || response.ok) {
    window.location.href = "/contacts.html";
  } else {
    setMessage("contact-page-message", "Не удалось удалить контакт.");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  setFooterYear();
  applyTokenFromHash();
  const token = getToken();
  if (!token) {
    window.location.href = "/login.html";
    return;
  }

  const form = document.getElementById("contact-form");
  if (form) {
    document.getElementById("btn-edit").addEventListener("click", () => setEditMode(form));
    document.getElementById("btn-save").addEventListener("click", () => saveContact());
    document.getElementById("btn-cancel").addEventListener("click", () => loadContact());
    document.getElementById("btn-delete").addEventListener("click", () => deleteContact());
  }

  loadContact();
});
