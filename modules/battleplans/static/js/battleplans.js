const bpIndicator = document.getElementById("bp-indicator");
const addPlanBtn = document.getElementById("add-plan-btn");
let currentBPDate = getTodayStr(); // track current BP date
let currentBPId = null; // track bp_id

let allBattlePlans = [];
const sortDescending = true;

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
        <span class="task-category">[${task.category}]</span>
        <button class="delete-task-btn">Delete</button>
      `;

      const checkbox = li.querySelector(".task-checkbox");
      const deleteBtn = li.querySelector(".delete-task-btn");

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

function parseMonthIndex(monthName) {
  if (!monthName) return 0;
  const m = monthName.toLowerCase().slice(0, 3);
  const months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
  const idx = months.indexOf(m);
  return idx === -1 ? 0 : idx;
}

async function loadBattlePlans() {
  try {
    const res = await fetch("/api/bps/list");
    if (!res.ok) throw new Error("Failed to fetch battle plans");
    const data = await res.json();

    allBattlePlans = Object.entries(data).map(([planName, dateObj]) => {
      const dayNum = parseInt(String(dateObj.day || "").replace(/^0+/, "") || "1", 10);
      const yearNum = dateObj.year ? parseInt(dateObj.year, 10) : new Date().getFullYear();
      const monthIdx = parseMonthIndex(dateObj.month || "");
      return { name: planName, dateObj, realDate: new Date(yearNum, monthIdx, dayNum), timestamp: new Date(yearNum, monthIdx, dayNum).getTime() };
    });

    allBattlePlans.sort((a, b) => sortDescending ? b.timestamp - a.timestamp : a.timestamp - b.timestamp);
    filterBattlePlans("");
  } catch (err) {
    console.error(err);
    plansContainer.innerHTML = `<p class="small">Failed to load battle plans.</p>`;
  }
}

function filterBattlePlans(searchTerm) {
  const filteredPlans = allBattlePlans.filter(plan => plan.name.toLowerCase().includes(searchTerm.toLowerCase()));
  plansContainer.innerHTML = "";
  if (filteredPlans.length === 0 && searchTerm) {
    plansContainer.innerHTML = `<p class="small">No battle plans found matching "${searchTerm}"</p>`;
    return;
  }
  filteredPlans.forEach(({ name, dateObj }) => {
    const btn = document.createElement("button");
    btn.className = "bp-item";
    btn.innerHTML = `<p class="bp-text">${name}</p>
      <div class="bp-date"><span class="bp-month">${dateObj.month}</span><br><span class="bp-day">${dateObj.day}</span></div>`;
    btn.addEventListener("click", () => loadFullBP(dateObj));
    plansContainer.appendChild(btn);
  });
}

// Search listener
const searchBar = document.getElementById("search-bar");
const clearSearchBtn = document.createElement("button");
clearSearchBtn.id = "clear-search";
clearSearchBtn.style.display = "none";
clearSearchBtn.textContent = "×";
searchBar.insertAdjacentElement('afterend', clearSearchBtn);

searchBar.addEventListener("input", (e) => {
  const val = e.target.value;
  clearSearchBtn.style.display = val ? "block" : "none";
  filterBattlePlans(val);
});

clearSearchBtn.addEventListener("click", () => {
  searchBar.value = "";
  filterBattlePlans("");
  clearSearchBtn.style.display = "none";
  searchBar.focus();
});

document.addEventListener("DOMContentLoaded", () => {
  loadBattlePlans();
  loadFullBP({ day: String(new Date().getDate()).padStart(2,"0"), month: new Date().toLocaleString("default",{month:"long"}) });
});

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