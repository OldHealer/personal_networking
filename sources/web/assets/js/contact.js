import { setFooterYear, setMessage, initTheme, setupThemeToggle, getToken, applyTokenFromHash, handleUnauthorized } from "./ui.js";

function escapeHtml(s) {
  if (s == null) return "";
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

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

const CONTACT_SECTION_FIELDS = {
  main: ["full_name", "phone", "email", "address", "relationship_type"],
  personal: ["family_status", "birthday", "hobbies", "interests"],
  plans: ["goals", "ambitions"],
};

const CONTACT_RELATIONSHIP_VALUES = new Set([
  "business", "colleague", "client", "partner", "mentor", "mentee",
  "personal", "friend", "acquaintance", "family", "other",
]);

function fromFormDataForKeys(form, keysSet) {
  const fd = new FormData(form);
  const listFields = ["hobbies", "interests", "goals", "promises"];
  const relationshipAllowed = CONTACT_RELATIONSHIP_VALUES;
  const payload = {};
  for (const [key, value] of fd.entries()) {
    if (keysSet != null && !keysSet.has(key)) continue;
    if (listFields.includes(key)) {
      const lines = String(value || "").split("\n").map((s) => s.trim()).filter(Boolean);
      payload[key] = lines;
    } else if (key === "relationship_type") {
      const v = String(value || "").trim();
      if (relationshipAllowed.has(v)) {
        payload[key] = v;
      }
      // если значение невалидно или пустое — не отправляем поле в PATCH
    } else if (key === "birthday") {
      payload[key] = value || null;
    } else {
      payload[key] = value === "" ? null : value;
    }
  }
  return payload;
}

function fromFormData(form) {
  return fromFormDataForKeys(form, null);
}

function contactToFormValues(c) {
  const listToText = (arr) => (Array.isArray(arr) && arr.length ? arr.join("\n") : "");
  const rel = CONTACT_RELATIONSHIP_VALUES.has(c.relationship_type) ? c.relationship_type : "";
  return {
    full_name: c.full_name ?? "",
    phone: c.phone ?? "",
    email: c.email ?? "",
    address: c.address ?? "",
    relationship_type: rel,
    family_status: c.family_status ?? "",
    birthday: toDateOnly(c.birthday),
    hobbies: listToText(c.hobbies),
    interests: listToText(c.interests),
    goals: listToText(c.goals),
    ambitions: c.ambitions ?? "",
  };
}

function fillForm(form, values) {
  for (const [name, value] of Object.entries(values)) {
    const el = form.elements[name];
    if (el) el.value = value ?? "";
  }
}

function autoResizeTextarea(ta) {
  if (!ta || ta.tagName !== "TEXTAREA") return;
  ta.style.height = "auto";
  ta.style.height = Math.max(ta.scrollHeight, 64) + "px";
}

function resizeAllTextareas() {
  document.querySelectorAll(".form-card .field textarea").forEach(autoResizeTextarea);
}

function fillContactForms(values) {
  const contactForm = document.getElementById("contact-form");
  if (contactForm) fillForm(contactForm, values);

  const plansForm = document.getElementById("contact-plans-form");
  if (plansForm) fillForm(plansForm, values);

  resizeAllTextareas();
}

function updateContactTitle(contact) {
  const titleEl = document.getElementById("contact-title");
  if (titleEl && contact) {
    titleEl.textContent = contact.full_name || "Контакт";
  }
}

let currentContact = null;
let currentLinks = [];
let currentInteractions = [];
let editingInteractionId = null;
let editingInteractionPromises = [];
let editingLinkId = null;

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
    const text = await response.text();
    let msg = "Не удалось загрузить контакт.";
    try {
      const j = JSON.parse(text);
      if (j.detail) msg += " " + (typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail));
    } catch (_) {
      if (text) msg += " " + text.slice(0, 200);
    }
    setMessage("contact-page-message", msg);
    return null;
  }
  try {
    return await response.json();
  } catch (_) {
    setMessage("contact-page-message", "Не удалось загрузить контакт: ответ сервера не JSON.");
    return null;
  }
}

function renderPromises(contact) {
  const listEl = document.getElementById("promises-items");
  const emptyEl = document.getElementById("promises-empty");
  if (!listEl || !emptyEl) return;

  const promises = Array.isArray(contact?.promises) ? contact.promises : [];
  listEl.innerHTML = "";
  if (!promises.length) {
    emptyEl.style.display = "block";
    return;
  }
  emptyEl.style.display = "none";

  promises.forEach((p) => {
    const li = document.createElement("li");
    const text = typeof p === "string" ? p : p.text || JSON.stringify(p);
    const direction = typeof p === "object" ? p.direction : null;
    const completedAt = typeof p === "object" ? p.completed_at : null;
    const dirLabel = direction === "theirs"
      ? `<span class="promise-direction promise-direction--theirs">Он/она:</span> `
      : direction === "mine"
        ? `<span class="promise-direction promise-direction--mine">Я:</span> `
        : "";
    li.className = "promise-item";
    li.innerHTML = `
      <span class="promise-text">${dirLabel}${escapeHtml(text)}</span>
      ${completedAt ? `<span class="muted promise-completed-at">выполнено ${new Date(completedAt).toLocaleString("ru")}</span>` : ""}
    `;
    if (typeof p === "object" && p.id) {
      if (!completedAt) {
        const complete = document.createElement("button");
        complete.type = "button";
        complete.className = "promise-complete-btn";
        complete.title = "Отметить выполненным";
        complete.setAttribute("aria-label", "Отметить выполненным");
        complete.innerHTML = "<span aria-hidden=\"true\">✓</span> Выполнить";
        complete.addEventListener("click", () => completePromise(p.id));
        li.appendChild(complete);

        const edit = document.createElement("button");
        edit.type = "button";
        edit.className = "promise-icon-btn";
        edit.title = "Редактировать";
        edit.setAttribute("aria-label", "Редактировать");
        edit.innerHTML = "✎";
        edit.addEventListener("click", () => startEditingPromise(li, p));
        li.appendChild(edit);
      }
      const del = document.createElement("button");
      del.type = "button";
      del.className = "promise-icon-btn promise-icon-btn--danger";
      del.title = "Удалить";
      del.setAttribute("aria-label", "Удалить");
      del.innerHTML = "🗑";
      del.addEventListener("click", () => deletePromise(p.id));
      li.appendChild(del);
    }
    listEl.appendChild(li);
  });
}

const RELATIONSHIP_TYPE_LABELS = {
  acquaintance: "Знакомый",
  friend: "Друг",
  colleague: "Коллега",
  business: "Деловой партнёр",
  mentor: "Наставник",
  mentee: "Подопечный",
  spouse: "Партнёр/супруг",
  parent: "Родитель",
  child: "Ребёнок",
  sibling: "Брат/сестра",
  relative: "Родственник",
  other: "Другое",
};

function getRelationshipTypeLabel(type) {
  return RELATIONSHIP_TYPE_LABELS[type] || type || "Другое";
}

function getOtherContactName(otherId) {
  if (!linkContactsList.length) return "Контакт";
  const c = linkContactsList.find((x) => String(x.id) === String(otherId));
  return c ? (c.full_name || "Без имени") : "Контакт";
}

function resetLinkForm() {
  const form = document.getElementById("link-form");
  const submitBtn = document.getElementById("link-submit-button");
  const cancelBtn = document.getElementById("link-cancel-edit");
  const searchInput = document.getElementById("link-contact-search");
  const hiddenInput = document.getElementById("link-contact-id");

  editingLinkId = null;

  if (form) form.reset();
  if (searchInput) { searchInput.value = ""; searchInput.disabled = false; }
  if (hiddenInput) hiddenInput.value = "";
  if (submitBtn) submitBtn.textContent = "Сохранить связь";
  if (cancelBtn) cancelBtn.hidden = true;
  setMessage("link-message", "");
}

function startEditingLink(link) {
  const form = document.getElementById("link-form");
  const submitBtn = document.getElementById("link-submit-button");
  const cancelBtn = document.getElementById("link-cancel-edit");
  const searchInput = document.getElementById("link-contact-search");
  const hiddenInput = document.getElementById("link-contact-id");
  if (!form || !link) return;

  editingLinkId = String(link.id);

  const otherId = String(link.contact_id_a) === String(currentContact.id) ? link.contact_id_b : link.contact_id_a;
  const otherName = getOtherContactName(otherId);

  if (searchInput) { searchInput.value = otherName; searchInput.disabled = true; }
  if (hiddenInput) hiddenInput.value = String(otherId);
  if (form.elements.relationship_type) form.elements.relationship_type.value = link.relationship_type || "";
  if (form.elements.context) form.elements.context.value = link.context || "";
  if (form.elements.is_directed) form.elements.is_directed.checked = Boolean(link.is_directed);

  if (submitBtn) submitBtn.textContent = "Сохранить изменения";
  if (cancelBtn) cancelBtn.hidden = false;

  setMessage("link-message", "Режим редактирования связи.");
  const viewportH = window.innerHeight || document.documentElement.clientHeight;
  const rect = form.getBoundingClientRect();
  const padding = 80;
  const isInView = rect.top >= -padding && rect.bottom <= viewportH + padding;
  if (!isInView) form.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function deleteLink(linkId) {
  const id = getContactId();
  const token = getToken();
  if (!id || !token || !linkId) return;
  if (!confirm("Удалить эту связь?")) return;

  setMessage("link-message", "Удаляем связь...");
  const response = await fetch(`/api/v1/contacts/${id}/links/${linkId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (response.status === 401) { handleUnauthorized(response); return; }
  if (response.status === 204 || response.ok) {
    if (editingLinkId === String(linkId)) resetLinkForm();
    setMessage("link-message", "Связь удалена.");
    setTimeout(() => setMessage("link-message", ""), 2000);
    await fetchLinks();
    return;
  }
  const text = await response.text();
  setMessage("link-message", `Ошибка удаления: ${text}`);
}

function renderLinks() {
  const listEl = document.getElementById("links-items");
  const emptyEl = document.getElementById("links-empty");
  if (!listEl || !emptyEl) return;

  listEl.innerHTML = "";
  if (!currentLinks.length) {
    emptyEl.style.display = "block";
    return;
  }
  emptyEl.style.display = "none";

  currentLinks.forEach((link) => {
    const li = document.createElement("li");
    li.className = "link-item";
    const typeKey = link.relationship_type || "";
    const typeLabel = getRelationshipTypeLabel(typeKey);
    const context = link.context || "";
    const otherId =
      String(link.contact_id_a) === String(currentContact.id) ? link.contact_id_b : link.contact_id_a;
    const otherName = getOtherContactName(otherId);

    const content = document.createElement("div");
    content.className = "link-item-content";
    content.innerHTML = `
      <span><strong>${escapeHtml(typeLabel)}</strong> · ${escapeHtml(otherName)}</span>
      ${context ? `<span class="muted"> · ${escapeHtml(context)}</span>` : ""}
    `;

    const actions = document.createElement("div");
    actions.className = "link-item-actions";

    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "button button-small button-outline";
    editBtn.textContent = "Редактировать";
    editBtn.addEventListener("click", () => startEditingLink(link));

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "button button-small button-outline button-delete";
    deleteBtn.textContent = "Удалить";
    deleteBtn.addEventListener("click", () => deleteLink(link.id));

    actions.appendChild(editBtn);
    actions.appendChild(deleteBtn);
    li.appendChild(content);
    li.appendChild(actions);
    listEl.appendChild(li);
  });
}

function interactionPromisesToMineText(promises) {
  if (!Array.isArray(promises) || !promises.length) return "";
  return promises
    .filter((p) => typeof p === "string" || !p.direction || p.direction === "mine")
    .map((p) => (typeof p === "string" ? p : p?.text || ""))
    .filter(Boolean)
    .join("\n");
}

function interactionPromisesToTheirsText(promises) {
  if (!Array.isArray(promises) || !promises.length) return "";
  return promises
    .filter((p) => typeof p === "object" && p.direction === "theirs")
    .map((p) => p?.text || "")
    .filter(Boolean)
    .join("\n");
}

function buildInteractionPromisesFromTexts(mineText, theirsText, previousPromises = []) {
  const mineLines = String(mineText || "").split("\n").map((s) => s.trim()).filter(Boolean);
  const theirsLines = String(theirsText || "").split("\n").map((s) => s.trim()).filter(Boolean);

  const prevMine = previousPromises.filter(
    (p) => typeof p === "string" || !p.direction || p.direction === "mine"
  );
  const prevTheirs = previousPromises.filter(
    (p) => typeof p === "object" && p.direction === "theirs"
  );

  const result = [];

  mineLines.forEach((line, i) => {
    const prev = prevMine[i];
    if (prev && typeof prev === "object") {
      result.push({ ...prev, text: line, direction: "mine" });
    } else {
      result.push({ text: line, direction: "mine" });
    }
  });

  theirsLines.forEach((line, i) => {
    const prev = prevTheirs[i];
    if (prev && typeof prev === "object") {
      result.push({ ...prev, text: line, direction: "theirs" });
    } else {
      result.push({ text: line, direction: "theirs" });
    }
  });

  return result;
}

function resetInteractionForm() {
  const form = document.getElementById("interaction-form");
  const titleEl = document.getElementById("interaction-form-title");
  const submitBtn = document.getElementById("interaction-submit-button");
  const cancelBtn = document.getElementById("interaction-cancel-edit");

  editingInteractionId = null;
  editingInteractionPromises = [];

  if (form) {
    form.reset();
    // Автоматически подставляем текущее время чтобы не вводить вручную
    if (form.elements.occurred_at && !form.elements.occurred_at.value) {
      form.elements.occurred_at.value = toDatetimeLocal(new Date().toISOString());
    }
  }
  if (titleEl) titleEl.textContent = "Добавить взаимодействие";
  if (submitBtn) submitBtn.textContent = "Сохранить взаимодействие";
  if (cancelBtn) cancelBtn.hidden = true;
  setMessage("interaction-message", "");
}

async function withAnchoredScroll(el, asyncFn) {
  if (!el) return await asyncFn();
  const beforeTop = el.getBoundingClientRect().top;
  const result = await asyncFn();

  // Ждём следующий кадр, чтобы layout успел обновиться после DOM-изменений.
  await new Promise((resolve) => requestAnimationFrame(() => resolve()));

  const afterTop = el.getBoundingClientRect().top;
  const delta = afterTop - beforeTop;
  if (Math.abs(delta) > 0.5) window.scrollBy({ top: delta });
  return result;
}

function startEditingInteraction(interaction) {
  const form = document.getElementById("interaction-form");
  const titleEl = document.getElementById("interaction-form-title");
  const submitBtn = document.getElementById("interaction-submit-button");
  const cancelBtn = document.getElementById("interaction-cancel-edit");

  if (!form || !interaction) return;

  editingInteractionId = String(interaction.id);
  editingInteractionPromises = Array.isArray(interaction.promises) ? interaction.promises : [];

  form.elements.occurred_at.value = toDatetimeLocal(interaction.occurred_at);
  form.elements.channel.value = interaction.channel ?? "";
  form.elements.notes.value = interaction.notes ?? "";
  form.elements.promises_mine.value = interactionPromisesToMineText(editingInteractionPromises);
  form.elements.promises_theirs.value = interactionPromisesToTheirsText(editingInteractionPromises);

  if (titleEl) titleEl.textContent = "Редактировать взаимодействие";
  if (submitBtn) submitBtn.textContent = "Сохранить изменения";
  if (cancelBtn) cancelBtn.hidden = false;

  setMessage("interaction-message", "Режим редактирования включён.");
  // Не двигаем прокрутку, если форма "Взаимодействия" уже видима.
  const viewportH = window.innerHeight || document.documentElement.clientHeight;
  const rect = form.getBoundingClientRect();
  const padding = 80;
  const isInView = rect.top >= -padding && rect.bottom <= viewportH + padding;
  if (!isInView) form.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderInteractions() {
  const listEl = document.getElementById("interactions-items");
  const emptyEl = document.getElementById("interactions-empty");
  if (!listEl || !emptyEl) return;

  listEl.innerHTML = "";
  if (!currentInteractions.length) {
    emptyEl.style.display = "block";
    return;
  }
  emptyEl.style.display = "none";

  currentInteractions.forEach((it) => {
    const li = document.createElement("li");
    li.className = "interaction-item";
    const dt = it.occurred_at ? new Date(it.occurred_at).toLocaleString("ru") : "";
    const channel = it.channel || "";
    const notes = it.notes || "";
    const promises = Array.isArray(it.promises) ? it.promises : [];
    const promisesText = promises
      .map((p) => {
        const t = typeof p === "string" ? p : p.text || JSON.stringify(p);
        const dir = typeof p === "object" ? p.direction : null;
        const prefix = dir === "theirs" ? "он/она: " : dir === "mine" ? "я: " : "";
        return prefix + t;
      })
      .join("; ");
    li.innerHTML = `
      <div class="interaction-item-content">
        <div><strong>${escapeHtml(dt || "Без даты")}</strong>${channel ? ` · ${escapeHtml(channel)}` : ""}</div>
        ${notes ? `<div>${escapeHtml(notes)}</div>` : ""}
        ${promisesText ? `<div class="muted">Обещания: ${escapeHtml(promisesText)}</div>` : ""}
      </div>
    `;

    const actions = document.createElement("div");
    actions.className = "interaction-item-actions";

    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "button button-small button-outline";
    editBtn.textContent = "Редактировать";
    editBtn.addEventListener("click", () => startEditingInteraction(it));

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "button button-small button-outline button-delete";
    deleteBtn.textContent = "Удалить";
    deleteBtn.addEventListener("click", () => deleteInteraction(it.id));

    actions.appendChild(editBtn);
    actions.appendChild(deleteBtn);
    li.appendChild(actions);
    listEl.appendChild(li);
  });
}

async function loadContact() {
  const id = getContactId();
  if (!id) {
    window.location.href = "/contacts.html";
    return;
  }
  const loadingEl = document.getElementById("contact-loading");
  const contentEl = document.getElementById("contact-content");
  loadingEl.style.display = "block";
  contentEl.style.display = "none";
  setMessage("contact-page-message", "");

  try {
    const contact = await fetchContact(id);
    if (!contact) {
      loadingEl.style.display = "none";
      contentEl.style.display = "block";
      return;
    }
    currentContact = contact;
    fillContactForms(contactToFormValues(contact));
    updateContactTitle(contact);
    loadingEl.style.display = "none";
    contentEl.style.display = "block";

    renderPromises(contact);
    await fetchContactsForLinkAutocomplete();
    await Promise.all([fetchLinks(), fetchInteractions()]);
  } catch (e) {
    loadingEl.style.display = "none";
    contentEl.style.display = "block";
    setMessage("contact-page-message", "Ошибка загрузки: " + (e && e.message ? e.message : String(e)));
    console.error("loadContact error", e);
  }
}

function setSectionMessage(sectionKey, text) {
  const el = document.querySelector(`[data-section-message="${sectionKey}"]`);
  if (el) {
    el.textContent = text || "";
  }
}

async function saveContactSection(sectionKey, triggerEl) {
  const id = getContactId();
  if (!id || !currentContact) return;
  const fields = CONTACT_SECTION_FIELDS[sectionKey];
  if (!fields || !fields.length) return;
  const form = triggerEl?.closest("form") || document.getElementById("contact-form");
  const keysSet = new Set(fields);
  const payload = fromFormDataForKeys(form, keysSet);
  if ("relationship_type" in payload && (payload.relationship_type === null || payload.relationship_type === "")) {
    delete payload.relationship_type;
  }
  setSectionMessage(sectionKey, "Сохранение...");
  const response = await fetch(`/api/v1/contacts/${id}`, {
    method: "PATCH",
    headers: apiHeaders(),
    body: JSON.stringify(payload),
  });
  if (response.status === 401) {
    handleUnauthorized(response);
    setSectionMessage(sectionKey, "");
    return;
  }
  if (!response.ok) {
    const text = await response.text();
    setSectionMessage(sectionKey, `Ошибка: ${text}`);
    return;
  }
  const updated = await response.json();
  currentContact = updated;
  fillContactForms(contactToFormValues(updated));
  updateContactTitle(updated);
  setSectionMessage(sectionKey, "Сохранено.");
  setTimeout(() => setSectionMessage(sectionKey, ""), 2000);
}

async function saveContact() {
  const id = getContactId();
  if (!id || !currentContact) return;
  const form = document.getElementById("contact-form");
  const payload = fromFormData(form);
  if ("relationship_type" in payload && (payload.relationship_type === null || payload.relationship_type === "")) {
    delete payload.relationship_type;
  }
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
  updateContactTitle(updated);
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

async function fetchLinks() {
  const id = getContactId();
  const token = getToken();
  if (!id || !token) return;
  const response = await fetch(`/api/v1/contacts/${id}/links`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (response.status === 401) {
    handleUnauthorized(response);
    return;
  }
  if (!response.ok) {
    setMessage("link-message", "Не удалось загрузить связи.");
    return;
  }
  currentLinks = await response.json();
  renderLinks();
}

async function fetchInteractions() {
  const id = getContactId();
  const token = getToken();
  if (!id || !token) return;
  const response = await fetch(`/api/v1/contacts/${id}/interactions`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (response.status === 401) {
    handleUnauthorized(response);
    return;
  }
  if (!response.ok) {
    setMessage("interaction-message", "Не удалось загрузить взаимодействия.");
    return;
  }
  currentInteractions = await response.json();
  renderInteractions();
}

/** Список контактов для автодополнения в форме «Связи». */
let linkContactsList = [];

function filterContactsBySearch(items, query, excludeId) {
  const q = (query || "").trim().toLowerCase();
  if (!q) return items.filter((c) => String(c.id) !== String(excludeId));
  const words = q.split(/\s+/).filter(Boolean);
  if (words.length === 0) return items.filter((c) => String(c.id) !== String(excludeId));
  return items.filter((c) => {
    if (String(c.id) === String(excludeId)) return false;
    const rawName = (c.full_name || "").trim();
    const rawEmail = (c.email || "").trim();
    const name = rawName.toLowerCase().replace(/\s+/g, " ");
    const email = rawEmail.toLowerCase().replace(/\s+/g, " ");
    return words.every((w) => name.includes(w) || (email && email.includes(w)));
  });
}

/** Показать список подсказок (контакты или сообщение при пустом списке). */
function showLinkSuggestions(items, options = {}) {
  const { emptyMessage = "Нет контактов", noResultsMessage = "Ничего не найдено", isRetryMessage = false } = options;
  const ul = document.getElementById("link-contact-suggestions");
  const input = document.getElementById("link-contact-search");
  if (!ul || !input) return;
  ul.innerHTML = "";
  ul.setAttribute("aria-hidden", "false");
  input.setAttribute("aria-expanded", "true");
  ul.classList.add("contact-suggestions-visible");

  if (items.length === 0) {
    const li = document.createElement("li");
    li.className = "contact-suggestions-message";
    li.setAttribute("role", "option");
    li.setAttribute("aria-disabled", "true");
    li.textContent = emptyMessage;
    if (options.isRetryMessage) li.dataset.retry = "1";
    ul.appendChild(li);
    return;
  }
  items.slice(0, 15).forEach((c) => {
    const li = document.createElement("li");
    li.setAttribute("role", "option");
    li.dataset.id = String(c.id != null ? c.id : "");
    li.dataset.name = String(c.full_name || "Без имени");
    li.textContent = c.full_name || "Без имени";
    ul.appendChild(li);
  });
}

function hideLinkSuggestions() {
  const ul = document.getElementById("link-contact-suggestions");
  const input = document.getElementById("link-contact-search");
  if (!ul) return;
  ul.innerHTML = "";
  ul.setAttribute("aria-hidden", "true");
  ul.classList.remove("contact-suggestions-visible");
  if (input) input.setAttribute("aria-expanded", "false");
}

async function fetchContactsForLinkAutocomplete(forceRefetch = false) {
  if (!forceRefetch && linkContactsList.length > 0) return true;
  const token = getToken();
  if (!token) {
    linkContactsList = [];
    return false;
  }
  const perPage = 100;
  const maxPages = 10;
  let success = false;
  try {
    const all = [];
    for (let page = 1; page <= maxPages; page++) {
      const response = await fetch(
        `/api/v1/contacts?page=${page}&per_page=${perPage}&sort=name`,
        { headers: apiHeaders() }
      );
      if (!response.ok) {
        if (page === 1) linkContactsList = [];
        break;
      }
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
    linkContactsList = success ? all : [];
    return success;
  } catch (e) {
    linkContactsList = [];
    return false;
  }
}

function initLinkContactAutocomplete() {
  const input = document.getElementById("link-contact-search");
  const hidden = document.getElementById("link-contact-id");
  const ul = document.getElementById("link-contact-suggestions");
  if (!input || !hidden || !ul) return;

  let hideTimeout = null;

  input.addEventListener("focus", async () => {
    const ok = await fetchContactsForLinkAutocomplete();
    const query = input.value.trim();
    const currentId = getContactId();
    const filtered = filterContactsBySearch(linkContactsList, query, currentId);
    showLinkSuggestions(filtered, {
      emptyMessage: ok
        ? (linkContactsList.length === 0 ? "Нет контактов" : "Введите имя или email для поиска")
        : "Не удалось загрузить список. Кликните для повторной попытки.",
      noResultsMessage: "Ничего не найдено",
      isRetryMessage: !ok,
    });
  });

  input.addEventListener("input", () => {
    clearTimeout(hideTimeout);
    const query = input.value.trim();
    const currentId = getContactId();
    const filtered = filterContactsBySearch(linkContactsList, query, currentId);
    showLinkSuggestions(filtered, {
      emptyMessage: linkContactsList.length === 0 ? "Загрузите список (кликните в поле)" : "Ничего не найдено",
      noResultsMessage: "Ничего не найдено",
    });
  });

  input.addEventListener("blur", () => {
    hideTimeout = setTimeout(hideLinkSuggestions, 150);
  });

  ul.addEventListener("mousedown", (e) => {
    e.preventDefault();
    const li = e.target.closest("li[role=option]");
    if (!li) return;
    if (li.dataset.retry === "1") {
      hideLinkSuggestions();
      fetchContactsForLinkAutocomplete(true).then((ok) => {
        const filtered = filterContactsBySearch(linkContactsList, input.value.trim(), getContactId());
        showLinkSuggestions(filtered, {
          emptyMessage: ok ? "Введите имя или email для поиска" : "Не удалось загрузить список. Кликните для повторной попытки.",
          isRetryMessage: !ok,
        });
      });
      return;
    }
    if (li.classList.contains("contact-suggestions-message")) return;
    const id = (li.dataset.id || "").trim();
    const name = (li.dataset.name || "").trim();
    if (!id) return;
    hidden.value = id;
    input.value = name;
    hideLinkSuggestions();
    input.setAttribute("aria-expanded", "false");
  });

  ul.addEventListener("click", (e) => {
    const li = e.target.closest("li[role=option]");
    if (!li || li.classList.contains("contact-suggestions-message")) return;
    const id = (li.dataset.id || "").trim();
    const name = (li.dataset.name || "").trim();
    if (!id) return;
    hidden.value = id;
    input.value = name;
    hideLinkSuggestions();
  });
}

async function createLink(event) {
  event.preventDefault();
  const id = getContactId();
  const token = getToken();
  if (!id || !token) {
    window.location.href = "/login.html";
    return;
  }
  const form = event.target;
  const fd = new FormData(form);
  const relationshipType = String(fd.get("relationship_type") || "").trim() || "other";
  const context = String(fd.get("context") || "").trim() || null;
  const isDirected = fd.get("is_directed") === "on";

  if (editingLinkId) {
    const payload = { relationship_type: relationshipType, context, is_directed: isDirected };
    setMessage("link-message", "Сохраняем изменения...");
    const response = await fetch(`/api/v1/contacts/${id}/links/${editingLinkId}`, {
      method: "PATCH",
      headers: apiHeaders(),
      body: JSON.stringify(payload),
    });
    if (response.status === 401) { handleUnauthorized(response); return; }
    if (!response.ok) {
      const text = await response.text();
      setMessage("link-message", `Ошибка: ${text}`);
      return;
    }
    resetLinkForm();
    setMessage("link-message", "Связь обновлена.");
    setTimeout(() => setMessage("link-message", ""), 2000);
    await fetchLinks();
    return;
  }

  const contactIdB = String(fd.get("contact_id_b") || "").trim();
  if (!contactIdB) {
    setMessage("link-message", "Выберите контакт из списка (начните вводить имя и нажмите на контакт в списке).");
    return;
  }
  const payload = {
    contact_id_b: contactIdB,
    relationship_type: relationshipType,
    context,
    is_directed: isDirected,
  };
  setMessage("link-message", "Создаём связь...");
  const response = await fetch(`/api/v1/contacts/${id}/links`, {
    method: "POST",
    headers: apiHeaders(),
    body: JSON.stringify(payload),
  });
  if (response.status === 401) { handleUnauthorized(response); return; }
  if (!response.ok) {
    const text = await response.text();
    setMessage("link-message", `Ошибка: ${text}`);
    return;
  }
  resetLinkForm();
  setMessage("link-message", "Связь создана.");
  setTimeout(() => setMessage("link-message", ""), 2000);
  await fetchLinks();
}

async function saveInteraction(event) {
  event.preventDefault();
  const id = getContactId();
  const token = getToken();
  if (!id || !token) {
    window.location.href = "/login.html";
    return;
  }
  const form = event.target;
  const fd = new FormData(form);
  const promises = buildInteractionPromisesFromTexts(fd.get("promises_mine"), fd.get("promises_theirs"), editingInteractionPromises);
  const occurredRaw = fd.get("occurred_at");
  const payload = {
    occurred_at: occurredRaw ? new Date(occurredRaw).toISOString() : new Date().toISOString(),
    channel: String(fd.get("channel") || "").trim() || null,
    notes: String(fd.get("notes") || "").trim() || null,
    promises,
  };

  if (!editingInteractionId) {
    payload.mentions = [];
  }

  const isEdit = Boolean(editingInteractionId);
  setMessage("interaction-message", isEdit ? "Сохраняем изменения..." : "Сохраняем взаимодействие...");
  const response = await fetch(
    isEdit
      ? `/api/v1/contacts/${id}/interactions/${editingInteractionId}`
      : `/api/v1/contacts/${id}/interactions`,
    {
      method: isEdit ? "PATCH" : "POST",
      headers: apiHeaders(),
      body: JSON.stringify(payload),
    }
  );
  if (response.status === 401) {
    handleUnauthorized(response);
    return;
  }
  if (!response.ok) {
    const text = await response.text();
    setMessage("interaction-message", `Ошибка: ${text}`);
    return;
  }
  const anchorEl = document.getElementById("interaction-form");
  await withAnchoredScroll(anchorEl, async () => {
    resetInteractionForm();
    setMessage("interaction-message", isEdit ? "Взаимодействие обновлено." : "Взаимодействие добавлено.");
    setTimeout(() => setMessage("interaction-message", ""), 2000);
    await Promise.all([loadContact(), fetchInteractions()]);
  });
}

async function deleteInteraction(interactionId) {
  const id = getContactId();
  const token = getToken();
  if (!id || !token) {
    window.location.href = "/login.html";
    return;
  }
  if (!interactionId) return;
  if (!confirm("Удалить это взаимодействие?")) return;

  const isDeletingCurrentEdit = editingInteractionId != null && String(editingInteractionId) === String(interactionId);
  const anchorEl = document.getElementById("interaction-form");

  await withAnchoredScroll(anchorEl, async () => {
    setMessage("interaction-message", "Удаляем взаимодействие...");
    const response = await fetch(`/api/v1/contacts/${id}/interactions/${interactionId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });

    if (response.status === 401) {
      handleUnauthorized(response);
      return;
    }

    if (response.status === 204 || response.ok) {
      if (isDeletingCurrentEdit) resetInteractionForm();
      setMessage("interaction-message", "Взаимодействие удалено.");
      setTimeout(() => setMessage("interaction-message", ""), 2000);
      await fetchInteractions();
      return;
    }

    const text = await response.text();
    setMessage("interaction-message", `Ошибка удаления: ${text}`);
  });
}

async function completePromise(promiseId) {
  const id = getContactId();
  const token = getToken();
  if (!id || !token) return;
  const response = await fetch(`/api/v1/contacts/${id}/promises/${promiseId}/complete`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (response.status === 401) {
    handleUnauthorized(response);
    return;
  }
  if (!response.ok) {
    const text = await response.text();
    setMessage("contact-page-message", `Не удалось отметить обещание выполненным: ${text}`);
    return;
  }
  await loadContact();
  await fetchInteractions();
}

async function updatePromiseText(promiseId, newText) {
  const id = getContactId();
  const token = getToken();
  if (!id || !token) return false;
  const response = await fetch(`/api/v1/contacts/${id}/promises/${promiseId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ text: newText }),
  });
  if (response.status === 401) { handleUnauthorized(response); return false; }
  if (!response.ok) {
    const text = await response.text();
    setMessage("contact-page-message", `Не удалось обновить обещание: ${text}`);
    return false;
  }
  await loadContact();
  await fetchInteractions();
  return true;
}

async function deletePromise(promiseId) {
  if (!window.confirm("Удалить это обещание?")) return;
  const id = getContactId();
  const token = getToken();
  if (!id || !token) return;
  const response = await fetch(`/api/v1/contacts/${id}/promises/${promiseId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (response.status === 401) { handleUnauthorized(response); return; }
  if (!response.ok) {
    const text = await response.text();
    setMessage("contact-page-message", `Не удалось удалить обещание: ${text}`);
    return;
  }
  await loadContact();
  await fetchInteractions();
}

function startEditingPromise(li, promise) {
  const originalText = typeof promise === "object" ? (promise.text || "") : String(promise);
  const direction = typeof promise === "object" ? promise.direction : null;
  const dirLabel = direction === "theirs"
    ? `<span class="promise-direction promise-direction--theirs">Он/она:</span>`
    : direction === "mine"
      ? `<span class="promise-direction promise-direction--mine">Я:</span>`
      : "";
  li.innerHTML = "";
  li.classList.add("promise-item--editing");
  const wrap = document.createElement("span");
  wrap.className = "promise-text promise-edit-wrap";
  wrap.innerHTML = dirLabel + " ";
  const input = document.createElement("input");
  input.type = "text";
  input.className = "promise-edit-input";
  input.value = originalText;
  wrap.appendChild(input);
  li.appendChild(wrap);

  const save = document.createElement("button");
  save.type = "button";
  save.className = "promise-complete-btn";
  save.textContent = "Сохранить";
  const cancel = document.createElement("button");
  cancel.type = "button";
  cancel.className = "promise-icon-btn";
  cancel.title = "Отменить";
  cancel.setAttribute("aria-label", "Отменить");
  cancel.innerHTML = "✕";
  li.appendChild(save);
  li.appendChild(cancel);
  input.focus();
  input.setSelectionRange(input.value.length, input.value.length);

  const doSave = async () => {
    const newText = input.value.trim();
    if (!newText || newText === originalText) { await loadContact(); return; }
    await updatePromiseText(promise.id, newText);
  };
  save.addEventListener("click", doSave);
  cancel.addEventListener("click", () => { loadContact(); });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); doSave(); }
    else if (e.key === "Escape") { e.preventDefault(); loadContact(); }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  setupThemeToggle();
  setFooterYear();
  applyTokenFromHash();

  document.querySelectorAll(".form-card .field textarea").forEach((ta) => {
    ta.addEventListener("input", () => autoResizeTextarea(ta));
  });
  const token = getToken();
  if (!token) {
    window.location.href = "/login.html";
    return;
  }

  const form = document.getElementById("contact-form");
  const btnDelete = document.getElementById("btn-delete");
  if (btnDelete) btnDelete.addEventListener("click", () => deleteContact());

  document.getElementById("contact-content")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-save-section]");
    if (!btn) return;
    e.preventDefault();
    const sectionKey = btn.getAttribute("data-save-section");
    if (sectionKey) saveContactSection(sectionKey, btn);
  });

  const linkForm = document.getElementById("link-form");
  if (linkForm) {
    linkForm.addEventListener("submit", createLink);
    initLinkContactAutocomplete();
  }

  const linkCancelBtn = document.getElementById("link-cancel-edit");
  if (linkCancelBtn) {
    linkCancelBtn.addEventListener("click", resetLinkForm);
  }

  const interactionForm = document.getElementById("interaction-form");
  if (interactionForm) {
    interactionForm.addEventListener("submit", saveInteraction);
    resetInteractionForm();
  }

  const interactionCancelBtn = document.getElementById("interaction-cancel-edit");
  if (interactionCancelBtn) {
    interactionCancelBtn.addEventListener("click", resetInteractionForm);
  }

  loadContact();
  // Предзагрузка списка контактов для автодополнения в форме «Связи»
  fetchContactsForLinkAutocomplete();
});
