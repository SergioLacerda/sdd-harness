const state = {
  items: [],
  selected: new Set(),
  categories: new Set(),
};

function itemMap() {
  return new Map(state.items.map((item) => [item.id, item]));
}

function getSelectedCategories() {
  return [...document.querySelectorAll("[data-filter].active")].map((node) => node.dataset.filter);
}

function filterItems() {
  const term = document.getElementById("search").value.toLowerCase();
  const categories = getSelectedCategories();
  return state.items.filter((item) => {
    const text = `${item.id} ${item.title} ${item.description}`.toLowerCase();
    const matchesText = term === "" || text.includes(term);
    const matchesCategory = categories.length === 0 || categories.includes(item.category);
    return matchesText && matchesCategory;
  });
}

function resolveSelection() {
  const warnings = [];
  const resolved = new Set(state.selected);
  const byId = itemMap();
  const queue = [...state.selected];
  const visiting = new Set();
  while (queue.length > 0) {
    const itemId = queue.shift();
    if (itemId === undefined || visiting.has(itemId)) continue;
    visiting.add(itemId);
    const item = byId.get(itemId);
    if (!item) {
      warnings.push(`Unknown selected item: ${itemId}`);
      continue;
    }
    for (const dep of item.depends_on || []) {
      if (!byId.has(dep)) {
        warnings.push(`${item.id} references missing dependency ${dep}`);
        continue;
      }
      if (!resolved.has(dep)) {
        warnings.push(`${item.id} requires ${dep}`);
        resolved.add(dep);
        queue.push(dep);
      }
    }
  }
  return { warnings, resolved: [...resolved].sort() };
}

function updateWarnings() {
  const node = document.getElementById("warnings");
  const { warnings } = resolveSelection();
  if (warnings.length === 0) {
    node.classList.add("hidden");
    node.textContent = "";
    return;
  }
  node.classList.remove("hidden");
  node.innerHTML = warnings.map((warning) => `<div>${warning}</div>`).join("");
}

function updateSummary() {
  const { resolved } = resolveSelection();
  document.getElementById("summary").textContent = `${resolved.length} selected`;
}

function showStatus(message, type = "info") {
  const node = document.getElementById("status");
  if (message === "") {
    node.classList.add("hidden");
    node.textContent = "";
    node.dataset.kind = "";
    return;
  }
  node.classList.remove("hidden");
  node.dataset.kind = type;
  node.textContent = message;
}

function persistSelection() {
  localStorage.setItem("sdd-selector", JSON.stringify([...state.selected]));
}

function toggleSelection(itemId, checked) {
  if (checked) {
    state.selected.add(itemId);
  } else {
    state.selected.delete(itemId);
  }
  persistSelection();
  updateWarnings();
  updateSummary();
}

function renderFilters() {
  const node = document.getElementById("filters");
  const names = [...state.categories].sort();
  node.innerHTML = names.map((name) => `<button data-filter="${name}" type="button">${name}</button>`).join("");
  for (const button of node.querySelectorAll("[data-filter]")) {
    button.addEventListener("click", () => {
      button.classList.toggle("active");
      renderItems();
    });
  }
}

function renderItems() {
  const node = document.getElementById("items");
  const items = filterItems();
  node.innerHTML = items.map((item) => {
    const checked = state.selected.has(item.id) ? "checked" : "";
    const depends = item.depends_on.length === 0 ? "" : `<span class="pill">Depends: ${item.depends_on.join(", ")}</span>`;
    const itemType = item.item_type || "mandate";
    return `<article class="card" data-item-type="${itemType}">
      <label><input type="checkbox" data-item="${item.id}" ${checked}> ${item.id}</label>
      <h2>${item.title}</h2>
      <p>${item.description}</p>
      <div class="meta">
        <span class="pill pill--type pill--${itemType}">${itemType}</span>
        <span class="pill">${item.category}</span>
        <span class="pill">${item.mandatory ? "mandatory" : "optional"}</span>
        ${depends}
      </div>
    </article>`;
  }).join("");
  for (const input of node.querySelectorAll("[data-item]")) {
    input.addEventListener("change", (event) => {
      toggleSelection(event.target.dataset.item, event.target.checked);
    });
  }
}

function downloadSelection() {
  const { resolved } = resolveSelection();
  const payload = {
    version: "1.0",
    selected_ids: [...state.selected].sort(),
    resolved_ids: resolved,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "selector-selection.json";
  link.click();
  URL.revokeObjectURL(url);
}

function restoreSelection() {
  const stored = localStorage.getItem("sdd-selector");
  if (stored === null) return;
  try {
    for (const itemId of JSON.parse(stored)) {
      if (typeof itemId === "string") {
        state.selected.add(itemId);
      }
    }
  } catch {
    localStorage.removeItem("sdd-selector");
  }
}

function loadSelectionPayload(payload) {
  if (!payload || typeof payload !== "object") {
    throw new Error("Selection payload must be an object.");
  }
  if (typeof payload.version !== "string") {
    throw new Error("Selection payload version must be a string.");
  }
  const selectedIds = Array.isArray(payload.selected_ids)
    ? payload.selected_ids
    : payload.resolved_ids;
  if (!Array.isArray(selectedIds)) {
    throw new Error("Selection payload must include selected_ids or resolved_ids.");
  }
  const byId = itemMap();
  state.selected.clear();
  for (const itemId of selectedIds) {
    if (typeof itemId !== "string") {
      throw new Error("Selection ids must be strings.");
    }
    if (!byId.has(itemId)) {
      throw new Error(`Unknown selector ID: ${itemId}`);
    }
    state.selected.add(itemId);
  }
  persistSelection();
  renderItems();
  updateWarnings();
  updateSummary();
}

function importSelectionFile(file) {
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const payload = JSON.parse(String(reader.result));
      loadSelectionPayload(payload);
      showStatus(`Imported ${state.selected.size} selected item(s).`, "success");
    } catch (error) {
      showStatus(error.message || "Failed to import selection JSON.", "error");
    }
  };
  reader.onerror = () => {
    showStatus("Failed to read selection file.", "error");
  };
  reader.readAsText(file);
}

function clearSelection() {
  state.selected.clear();
  persistSelection();
  renderItems();
  updateWarnings();
  updateSummary();
  showStatus("Selection cleared.", "info");
}

async function boot() {
  const response = await fetch("data.json");
  const payload = await response.json();
  state.items = payload.items;
  for (const item of state.items) {
    state.categories.add(item.category);
  }
  restoreSelection();
  renderFilters();
  renderItems();
  updateWarnings();
  updateSummary();
  document.getElementById("search").addEventListener("input", renderItems);
  document.getElementById("export").addEventListener("click", downloadSelection);
  document.getElementById("import").addEventListener("click", () => {
    document.getElementById("import-file").click();
  });
  document.getElementById("import-file").addEventListener("change", (event) => {
    const [file] = event.target.files || [];
    if (!file) return;
    importSelectionFile(file);
    event.target.value = "";
  });
  document.getElementById("clear").addEventListener("click", clearSelection);
}

boot();
