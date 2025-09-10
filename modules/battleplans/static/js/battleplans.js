// ==================== Config ====================
const doNotifySuccess = true; // set to false to disable success notifications

// ==================== Navigation ====================
const backBtn = document.getElementById("back-btn");
backBtn.addEventListener("click", () => window.location.href = "/");

const bplist = document.getElementById("bplist");
const toggleBtn = document.getElementById("toggle-bplist-btn");
const plansContainer = document.getElementById("plans-container");

const taskList = document.getElementById("task-list");
const bpIndicator = document.getElementById("bp-indicator");

let currentBPDate = getTodayStr(); // track which BP is currently open
let currentBPId = null; // track bp_id for quota operations

function setOpenState(open) {
  if (open) {
    toggleBtn.setAttribute("aria-expanded", "true");
    bplist.removeAttribute("aria-hidden");
    bplist.removeAttribute("hidden");
    toggleBtn.textContent = "✕";
  } else {
    toggleBtn.setAttribute("aria-expanded", "false");
    bplist.setAttribute("aria-hidden", "true");
    toggleBtn.textContent = "☰";
  }
}

toggleBtn.addEventListener("click", () => {
  const isOpen = toggleBtn.getAttribute("aria-expanded") === "true";
  setOpenState(!isOpen);
});

if (window.innerWidth < 900) setOpenState(false);
else setOpenState(true);

// ==================== Battle Plans List ====================
async function loadBattlePlans() {
  try {
    const res = await fetch("/api/bps/list");
    if (!res.ok) throw new Error("Failed to fetch battle plans");
    const data = await res.json();

    plansContainer.innerHTML = "";
    Object.entries(data).forEach(([planName, dateObj]) => {
      const btn = document.createElement("button");
      btn.className = "bp-item";
      btn.innerHTML = `
        <p class="bp-text">${planName}</p>
        <div class="bp-date">
          <span class="bp-month">${dateObj.month}</span><br>
          <span class="bp-day">${dateObj.day}</span>
        </div>
      `;
      btn.addEventListener("click", () => loadFullBP(dateObj));
      plansContainer.appendChild(btn);
    });
  } catch (err) {
    console.error(err);
    plansContainer.innerHTML = `<p class="small">Failed to load battle plans.</p>`;
  }
}

let quotaStatus = document.getElementById("quota-status")

// ==================== Load Full BP ====================
async function loadFullBP({ day, month }, do_alert = true) {
  try {
    const year = new Date().getFullYear();
    const fullDateStr = `${day}-${month}-${year}`;
    currentBPDate = fullDateStr;

    const res = await fetch(`/api/bps/get/${fullDateStr}`);
    if (!res.ok) throw new Error("Failed to fetch full battle plan");
    const bpData = await res.json();

    currentBPId = bpData.bp_id || null;
    if (bpIndicator) bpIndicator.textContent = `BattlePlan: ${bpData.date || fullDateStr}`;

    // only run after we know the ID
    await loadQuotas(currentBPId, currentBPDate);
    await updateQuotaStatus(currentBPId);

    taskList.innerHTML = "";
    bpData.tasks.forEach(task => {
      const li = document.createElement("li");
      li.className = "task-item";
      li.dataset.id = task.id;

      li.innerHTML = `
        <input type="checkbox" class="task-checkbox" ${task.done ? "checked" : ""}>
        <span class="task-text">${task.text}</span>
        <button class="delete-task-btn">Delete</button>
      `;

      const checkbox = li.querySelector(".task-checkbox");
      const deleteBtn = li.querySelector(".delete-task-btn");

      // Checkbox toggle with guard
      checkbox.addEventListener("change", async () => {
        if (!(await ensureEditAllowed(checkbox))) return;
        const taskId = li.dataset.id;
        const state = checkbox.checked;
        try {
          const res = await fetch("/api/bps/task/set_status", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ task_id: taskId, state })
          });
          if (!res.ok) throw new Error("Failed to update task status");
        } catch (err) {
          console.error(err);
          if (do_alert) toast("Could not update task status. Reverting.", "error");
          checkbox.checked = !state;
        }
      });

      // Delete button with guard
      deleteBtn.addEventListener("click", async () => {
        if (!(await ensureEditAllowed(deleteBtn))) return;
        const taskId = li.dataset.id;
        try {
          const res = await fetch(`/api/bps/task/delete/${taskId}`, { method: "GET" });
          if (!res.ok) throw new Error("Failed to delete task");
          li.remove();
          if (doNotifySuccess) toast("Task deleted", "success");
        } catch (err) {
          console.error(err);
          if (do_alert) toast("Failed to delete task. Try again.");
        }
      });

      taskList.appendChild(li);
    });

    if (window.innerWidth < 900) setOpenState(false);
  } catch (err) {
    console.error(err);
    if (do_alert) toast("Failed to load full battle plan");

    taskList.innerHTML = `<p class='small'>There doesn't seem to be a BP For today.<br>Click 'New Battle Plan' to create one.</p>`;
    if (bpIndicator) bpIndicator.textContent = "No active Battle Plan";
    currentBPId = null;
  }
}

// ==================== Guard helpers ====================
async function ensureEditAllowed(target) {
  if (!shouldShowWarning(currentBPDate)) return true;

  const proceed = await showWarningModal();
  if (!proceed) {
    if (target) {
      target.blur();
      if ("checked" in target) target.checked = !target.checked;
      if ("value" in target) target.value = target.defaultValue || "";
    }
    return false;
  }
  return true;
}

// ==================== New Battle Plan ====================
const addPlanBtn = document.getElementById("add-plan-btn");
addPlanBtn.addEventListener("click", async () => {
  try {
    const now = new Date();
    const day = String(now.getDate()).padStart(2, "0");
    const month = now.toLocaleString("default", { month: "long" });
    const dateStr = `${day}-${month}-${now.getFullYear()}`;

    taskList.innerHTML = "";
    if (bpIndicator) bpIndicator.textContent = "";

    const res = await fetch(`/api/bps/create/${encodeURIComponent(dateStr)}`, { method: "GET" });
    if (res.status === 409) {
      toast("A battle plan for today already exists, loading today's BattlePlan.", "info");
      loadFullBP({ day, month });
      return;
    }
    if (!res.ok) throw new Error("Failed to create new battle plan");

    await loadBattlePlans();
    loadFullBP({ day, month });

    if (doNotifySuccess) toast("New BattlePlan created", "success");
    if (window.innerWidth < 900) setOpenState(false);
  } catch (err) {
    console.error(err);
    toast("Failed to create new battle plan", "error");
  }
});

// Auto-load today's BP
loadFullBP({ day: String(new Date().getDate()).padStart(2, "0"), month: new Date().toLocaleString("default", { month: "long" }) });

// ==================== Tasks ====================
const newTaskForm = document.getElementById("new-task-form");
const taskInput = document.getElementById("task-input");

newTaskForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!(await ensureEditAllowed(taskInput))) return;

  const text = taskInput.value.trim();
  if (!text || !currentBPId) {
    toast("No active BattlePlan. Create one first.", "error");
    return;
  }

  try {
    const res = await fetch("/api/bps/task/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bp_id: currentBPId, text })
    });
    if (!res.ok) throw new Error("Failed to add task");
    const newTask = await res.json();

    const li = document.createElement("li");
    li.className = "task-item";
    li.dataset.id = newTask.id;

    li.innerHTML = `
      <input type="checkbox" class="task-checkbox">
      <span class="task-text">${newTask.text}</span>
      <button class="delete-task-btn">Delete</button>
    `;

    li.querySelector(".task-checkbox").addEventListener("change", async (e) => {
      if (!(await ensureEditAllowed(e.target))) return;
      const taskId = li.dataset.id;
      const state = e.target.checked;
      try {
        const res = await fetch("/api/bps/task/set_status", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ task_id: taskId, state })
        });
        if (!res.ok) throw new Error("Failed to update task status");
        if (doNotifySuccess) toast("Task status updated", "success");
      } catch {
        e.target.checked = !state;
        toast("Could not update task status. Reverting.", "error");
      }
    });

    li.querySelector(".delete-task-btn").addEventListener("click", async () => {
      if (!(await ensureEditAllowed(li.querySelector(".delete-task-btn")))) return;
      const taskId = li.dataset.id;
      try {
        const res = await fetch(`/api/bps/task/delete/${taskId}`, { method: "GET" });
        if (!res.ok) throw new Error("Failed to delete task");
        li.remove();
        if (doNotifySuccess) toast("Task deleted", "success");
      } catch {
        toast("Failed to delete task. Try again.", "error");
      }
    });

    taskList.appendChild(li);
    taskInput.value = "";
  } catch (err) {
    console.error(err);
    toast("Failed to add new task.", "error");
  }
});

// ==================== Quota Handling ====================
const quotaList = document.getElementById("quota-list");

function debounce(fn, wait = 700) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
}

async function loadQuotas(bpId, bpDate = currentBPDate) {
  if (!bpId || !bpDate) return;
  try {
    const res = await fetch(`/api/bps/quota/list/${encodeURIComponent(bpDate)}`);
    if (!res.ok) throw new Error("Failed to load quotas");
    const quotas = await res.json();

    quotaList.innerHTML = "";
    quotas.forEach(quota => {
      const row = document.createElement("div");
      row.className = "quota-row";
      row.dataset.quotaId = quota.quota_id;

      row.innerHTML = `
        <span class="quota-name">${quota.name}</span>
        <input type="number" class="quota-done" value="${quota.done_amount || 0}" min="0"> /
        <input type="number" class="quota-needed" value="${quota.planned_amount || 0}" min="0">
      `;

      const neededInput = row.querySelector(".quota-needed");
      const doneInput = row.querySelector(".quota-done");

      neededInput.addEventListener("input", e => {
        const val = parseFloat(e.target.value);
        if (!isNaN(val)) debouncedSaveNeeded(quota.quota_id, val);
      });

      doneInput.addEventListener("input", e => {
        const val = parseFloat(e.target.value);
        if (!isNaN(val)) debouncedSaveDone(quota.quota_id, val);
      });

      quotaList.appendChild(row);
    });
  } catch (err) {
    console.error(err);
    toast("Failed to load quota info", "error");
  }
}

async function saveQuota(type, quotaId, value) {
  if (!currentBPId) return;
  let url, payload;

  if (type === "needed") {
    url = "/api/bps/quota/wanted/set";
    payload = { quota_id: quotaId, amount: value };
  } else {
    url = "/api/bps/quota/done/set";
    payload = { quota_id: quotaId, amount: value };
  }

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`Failed to save quota ${type}`);
    await updateQuotaStatus(currentBPId);
    if (doNotifySuccess) toast(`Quota ${type} saved`, "success");
  } catch (err) {
    console.error(err);
    toast(`Failed to save quota ${type}`, "error");
  }
}

async function updateQuotaStatus(bpId, bpDate = currentBPDate) {
  if (!bpId) return;
  try {
    const res = await fetch("/api/bps/quota/weekly", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date: bpDate })
    });
    if (!res.ok) {
      quotaStatus.textContent = "Production this week: N/A";
      return;
    }
    const weekly = await res.text();
    quotaStatus.textContent =
      `Production this week: ${weekly}`
  } catch {
    quotaStatus.textContent = "Production this week: N/A";
  }
}

const debouncedSaveNeeded = debounce((quotaId, v) => saveQuota("needed", quotaId, v), 700);
const debouncedSaveDone = debounce((quotaId, v) => saveQuota("done", quotaId, v), 700);

// ==================== Warning Modal ====================
const warningModal = document.getElementById("bp-warning-modal");
const warningCancel = document.getElementById("bp-warning-cancel");
const warningConfirm = document.getElementById("bp-warning-confirm");

function showWarningModal() {
  return new Promise((resolve) => {
    warningModal.classList.remove("hidden");
    const cleanup = () => {
      warningModal.classList.add("hidden");
      warningCancel.removeEventListener("click", onCancel);
      warningConfirm.removeEventListener("click", onConfirm);
    };
    function onCancel() { cleanup(); resolve(false); }
    function onConfirm() {
      cleanup();
      localStorage.setItem("bpWarningDismissedUntil", Date.now() + 30*60*1000);
      resolve(true);
    }
    warningCancel.addEventListener("click", onCancel);
    warningConfirm.addEventListener("click", onConfirm);
  });
}

function shouldShowWarning(dateStr) {
  const today = getTodayStr();
  if (dateStr === today) return false;
  const dismissedUntil = parseInt(localStorage.getItem("bpWarningDismissedUntil") || "0", 10);
  return Date.now() > dismissedUntil;
}

// ==================== Initial Load ====================
loadBattlePlans();

/* ---------- Control Buttons ---------- */
const clearBtn = document.getElementById("clear-btn");
const importBtn = document.getElementById("import-btn");
const helpBtn = document.getElementById("help-btn");

function getCurrentBPDate() { return currentBPDate || getTodayStr(); }

clearBtn.addEventListener("click", async () => {
  if (!currentBPId) return;
  try {
    const res = await fetch("/api/bps/clear", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ bp_id: currentBPId }) });
    if (!res.ok) throw new Error("Failed to clear BP");

    taskList.innerHTML = "";
    await loadQuotas(currentBPId);
    await updateQuotaStatus(currentBPId);
    if (doNotifySuccess) toast("Battle Plan cleared", "success");
  } catch {
    toast("Failed to clear BP", "error");
  }
});

importBtn.addEventListener("click", async () => {
  if (!currentBPId) return;
  try {
    const res = await fetch("/api/bps/yesterday_import", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ date_today: currentBPDate }) });
    if (!res.ok) throw new Error("Failed to import yesterday's BP");
    const [day, month] = currentBPDate.split("-");
    await loadFullBP({ day, month });
    if (doNotifySuccess) toast("Yesterday's BP imported", "success");
  } catch {
    toast("Failed to import yesterday's BP", "error");
  }
});

// Help Modal
const helpModal = document.getElementById("bp-help-modal");
const helpClose = document.getElementById("bp-help-close");
helpBtn.addEventListener("click", () => helpModal.classList.remove("hidden"));
helpClose.addEventListener("click", () => helpModal.classList.add("hidden"));

// Theme Toggle
const btn = document.getElementById("theme-toggle-btn");
btn.addEventListener("click", () => {
  const theme = document.body.dataset.theme === "light" ? "dark" : "light";
  document.body.dataset.theme = theme;
  localStorage.setItem("theme", theme);
});
document.body.dataset.theme = localStorage.getItem("theme") || "dark";

function getTodayStr() {
  const now = new Date();
  const day = String(now.getDate()).padStart(2, "0");
  const month = now.toLocaleString("default", { month: "long" });
  const year = now.getFullYear();
  return `${day}-${month}-${year}`;
}

// Elements
const addQuotaBtn = document.getElementById('add-quota-btn');
const addQuotaModal = document.getElementById('add-quota-modal');
const addQuotaCancel = document.getElementById('add-quota-cancel');
const addQuotaForm = document.getElementById('add-quota-form');

// --- Open / Close modal ---
addQuotaBtn.addEventListener('click', () => {
  addQuotaModal.classList.remove('hidden');
  document.getElementById('new-quota-name').focus();
});

addQuotaCancel.addEventListener('click', () => {
  addQuotaModal.classList.add('hidden');
});

// --- Handle adding new quota ---
addQuotaForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const name = document.getElementById('new-quota-name').value.trim();

  if(!name) return;

  try {
    const res = await fetch('/api/bps/quota/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        "bp_id": currentBPId,
        "quota_name": name,
      })
    });

    if(!res.ok) throw new Error('Failed to create quota');

    // Close modal and reset form
    addQuotaForm.reset();
    addQuotaModal.classList.add('hidden');

    // Reload quotas from DB
    await loadQuotas(currentBPId, currentBPDate);
  } catch (err) {
    console.error(err);
    alert('Error creating quota on server.');
  }
});