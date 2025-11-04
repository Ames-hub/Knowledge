// battleplans.js
const bpIndicator = document.getElementById("bp-indicator");
const addPlanBtn = document.getElementById("add-plan-btn");
let currentBPDate = getTodayStr(); // track current BP date
let currentBPId = null; // track bp_id
let selectedBPDate = null;

let allBattlePlans = [];
const sortDescending = true;

// Modal refs
const customDateModal = document.getElementById("custom-date-modal");
const customDateForm = document.getElementById("custom-date-form");
const customDateInput = document.getElementById("custom-date-input");
const customDateCancel = document.getElementById("custom-date-cancel");

// ----------- LOAD FULL BATTLEPLAN -----------
async function loadFullBP({ day, month }, do_alert = true) {
  try {
    const year = new Date().getFullYear();
    const fullDateStr = `${day}-${month}-${year}`;
    currentBPDate = fullDateStr;
    selectedBPDate = fullDateStr; // Set as selected

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

    // Update BP list highlighting
    updateBPListHighlighting();

    if (window.innerWidth < 900) setOpenState(false);
  } catch (err) {
    console.error(err);
    if (do_alert) toast("Failed to load full battle plan");

    taskList.innerHTML = `<p class='small'>There doesn't seem to be a BP For today.<br>Click 'New Battle Plan' to create one.</p>`;
    if (bpIndicator) bpIndicator.textContent = "No active Battle Plan";
    currentBPId = null;
    selectedBPDate = null;
    
    // Update BP list highlighting even on error
    updateBPListHighlighting();
  }
}

// ----------- HELPERS -----------
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
      const realDate = new Date(yearNum, monthIdx, dayNum);

      const weekdayName = realDate.toLocaleDateString("default", { weekday: "long" });
      const fullDateStr = `${String(dayNum).padStart(2,"0")}-${String(monthIdx+1).padStart(2,"0")}-${yearNum}`;

      return {
        name: weekdayName,
        dateObj,
        realDate,
        timestamp: realDate.getTime(),
        fullDateStr
      };
    });

    allBattlePlans.sort((a, b) => sortDescending ? b.timestamp - a.timestamp : a.timestamp - b.timestamp);
    filterBattlePlans("");
  } catch (err) {
    console.error(err);
    plansContainer.innerHTML = `<p class="small">Failed to load battle plans.</p>`;
  }
}

function filterBattlePlans(searchTerm) {
  const term = searchTerm.toLowerCase();

  const filteredPlans = allBattlePlans.filter(plan =>
    plan.name.toLowerCase().includes(term) ||
    plan.fullDateStr.toLowerCase().includes(term)
  );

  plansContainer.innerHTML = "";
  if (filteredPlans.length === 0 && searchTerm) {
    plansContainer.innerHTML = `<p class="small">No battle plans found matching "${searchTerm}"</p>`;
    return;
  }

  const today = new Date();
  const todayStr = `${today.getFullYear()}-${today.getMonth()}-${today.getDate()}`;

  filteredPlans.forEach(({ name, dateObj, realDate, fullDateStr }) => {
    const btn = document.createElement("button");
    btn.className = "bp-item";

    const planStr = `${realDate.getFullYear()}-${realDate.getMonth()}-${realDate.getDate()}`;
    
    // Highlight if it's today's BP
    if (planStr === todayStr) btn.classList.add("current-bp");
    
    // Highlight if it's the selected BP
    if (selectedBPDate === fullDateStr) btn.classList.add("selected-bp");

    btn.innerHTML = `<p class="bp-text">${name}</p>
      <div class="bp-date"><span class="bp-month">${dateObj.month}</span><br><span class="bp-day">${dateObj.day}</span></div>`;
    btn.addEventListener("click", () => loadFullBP(dateObj));
    plansContainer.appendChild(btn);
  });
}

// ----------- SEARCH SETUP -----------
const searchBar = document.getElementById("search-bar");
const clearSearchBtn = document.createElement("button");
clearSearchBtn.id = "clear-search";
clearSearchBtn.style.display = "none";
clearSearchBtn.textContent = "\ufffd";
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

// ----------- CREATE BATTLEPLAN -----------
async function createBattlePlanForDate(day, month, year = new Date().getFullYear()) {
  try {
    const dateStr = `${day}-${month}-${year}`;
    taskList.innerHTML = "";
    if (bpIndicator) bpIndicator.textContent = "";

    const res = await fetch(`/api/bps/create/${encodeURIComponent(dateStr)}`, { method: "GET" });
    if (res.status === 409) {
      toast(`A battle plan for ${dateStr} already exists, loading it.`, "info");
      loadFullBP({ day, month });
      return;
    }
    if (!res.ok) throw new Error("Failed to create new battle plan");

    await loadBattlePlans();
    loadFullBP({ day, month });

    if (doNotifySuccess) toast(`BattlePlan created for ${dateStr}`, "success");
    if (window.innerWidth < 900) setOpenState(false);
  } catch (err) {
    console.error(err);
    toast("Failed to create new battle plan", "error");
  }
}

function updateBPListHighlighting() {
  const bpItems = document.querySelectorAll('.bp-item');
  const today = new Date();
  const todayStr = `${today.getFullYear()}-${today.getMonth()}-${today.getDate()}`;
  
  bpItems.forEach(item => {
    // Remove existing highlight classes
    item.classList.remove('current-bp', 'selected-bp');
    
    // Extract date info from the item
    const monthText = item.querySelector('.bp-month').textContent;
    const dayText = item.querySelector('.bp-day').textContent;
    
    // Create a comparable date string
    const monthIdx = parseMonthIndex(monthText);
    const yearNum = today.getFullYear(); // Assuming current year
    const realDate = new Date(yearNum, monthIdx, parseInt(dayText));
    const planStr = `${realDate.getFullYear()}-${realDate.getMonth()}-${realDate.getDate()}`;
    
    // Highlight if it's today's BP
    if (planStr === todayStr) {
      item.classList.add('current-bp');
    }
    
    // Highlight if it's the selected BP
    if (selectedBPDate) {
      const [selectedDay, selectedMonth, selectedYear] = selectedBPDate.split('-');
      const selectedMonthIdx = parseMonthIndex(selectedMonth);
      const selectedDate = new Date(parseInt(selectedYear), selectedMonthIdx, parseInt(selectedDay));
      const selectedPlanStr = `${selectedDate.getFullYear()}-${selectedDate.getMonth()}-${selectedDate.getDate()}`;
      
      if (planStr === selectedPlanStr) {
        item.classList.add('selected-bp');
      }
    }
  });
}

// ----------- SHORT CLICK / LONG PRESS -----------
let pressTimer;
const longPressThreshold = 700; // ms

addPlanBtn.addEventListener("mousedown", startPress);
addPlanBtn.addEventListener("touchstart", startPress);
addPlanBtn.addEventListener("mouseup", clearPress);
addPlanBtn.addEventListener("mouseleave", clearPress);
addPlanBtn.addEventListener("touchend", clearPress);
addPlanBtn.addEventListener("touchcancel", clearPress);

function startPress(e) {
  e.preventDefault();
  pressTimer = setTimeout(() => {
    openCustomDateModal();
  }, longPressThreshold);
}

function clearPress(e) {
  if (pressTimer) {
    clearTimeout(pressTimer);
    if (e.type === "mouseup" || e.type === "touchend") createTodayBP();
  }
}

function createTodayBP() {
  const now = new Date();
  const day = String(now.getDate()).padStart(2, "0");
  const month = now.toLocaleString("default", { month: "long" });
  createBattlePlanForDate(day, month, now.getFullYear());
}

// ----------- CUSTOM DATE MODAL -----------
function openCustomDateModal() {
  customDateInput.value = "";
  customDateModal.classList.remove("hidden");
  customDateInput.focus();
}

function closeCustomDateModal() {
  customDateModal.classList.add("hidden");
}

customDateCancel.addEventListener("click", closeCustomDateModal);

customDateForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const dateValue = customDateInput.value;
  if (!dateValue) return;
  const [year, monthNum, day] = dateValue.split("-");
  const month = new Date(`${year}-${monthNum}-01`).toLocaleString("default", { month: "long" });
  createBattlePlanForDate(String(day).padStart(2,"0"), month, year);
  closeCustomDateModal();
});
