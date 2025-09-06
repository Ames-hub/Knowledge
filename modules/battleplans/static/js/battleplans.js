const backBtn = document.getElementById("back-btn");
backBtn.addEventListener("click", () => {
  window.location.href = "/";
});

const bplist = document.getElementById("bplist");
const toggleBtn = document.getElementById("toggle-bplist-btn");
const plansContainer = document.getElementById("plans-container");

const taskList = document.getElementById("task-list");
const bpIndicator = document.getElementById("bp-indicator");

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

/* ---------- Load Battle Plans list ---------- */
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

/* ---------- Load Full BP ---------- */
async function loadFullBP({ day, month }, do_alert=true) {
  try {
    const year = new Date().getFullYear();
    const fullDateStr = `${day}-${month}-${year}`;
    const res = await fetch(`/api/bps/get/${fullDateStr}`);
    if (!res.ok) throw new Error("Failed to fetch full battle plan");
    const bpData = await res.json();

    if (bpIndicator) bpIndicator.textContent = `BattlePlan: ${bpData.date || fullDateStr}`;

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

      // Checkbox toggle
      checkbox.addEventListener("change", async () => {
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
          if (do_alert) {
            toast("Could not update task status. Reverting.", "error");
          };
          console.error("Could not update task status. Reverting.");
          checkbox.checked = !state;
        }
      });

      // Delete button
      deleteBtn.addEventListener("click", async () => {
        const taskId = li.dataset.id;
        try {
          const res = await fetch(`/api/bps/task/delete/${taskId}`, {
            method: "GET",
          });
          if (!res.ok) throw new Error("Failed to delete task");
          li.remove();
        } catch (err) {
          console.error(err);
          if (do_alert) {
            toast("Failed to delete task. Try again.");
          };
          console.error(`Failed to delete task with ID ${taskId}, Try again.`);
        }
      });

      taskList.appendChild(li);
    });

    if (window.innerWidth < 900) setOpenState(false);
  } catch (err) {
    console.error(err);
    if (do_alert) {
      toast("Failed to load full battle plan");
    }
    console.error("Failed to load full battle plan");
    taskList.innerHTML = `<p class="small">There doesn't seem to be a BP For today.<br>How about we get started?</p>`;
    if (bpIndicator) bpIndicator.textContent = "BP not found";
  }
}

loadBattlePlans();

/* ---------- New Battle Plan ---------- */
const addPlanBtn = document.getElementById("add-plan-btn");

addPlanBtn.addEventListener("click", async () => {
  try {
    const now = new Date();
    const day = String(now.getDate()).padStart(2, "0");
    const month = now.toLocaleString("default", { month: "long" });
    const year = now.getFullYear();
    const dateStr = `${day}-${month}-${year}`;

    // Unload current BP
    taskList.innerHTML = "";
    if (bpIndicator) bpIndicator.textContent = "";

    // Create new BP
    const res = await fetch(`/api/bps/create/${encodeURIComponent(dateStr)}`, { method: "GET" });
    if (res.status === 409) {
      toast("A battle plan for today already exists, loading today's BattlePlan.", "info");
      loadFullBP({ day, month });
      return;
    }
    if (!res.ok) throw new Error("Failed to create new battle plan");

    // Reload list & load new BP
    await loadBattlePlans();
    loadFullBP({ day, month });

    if (window.innerWidth < 900) setOpenState(false);
  } catch (err) {
    console.error(err);
    toast("Failed to create new battle plan", "error");
  }
});

// Auto-load today's BP on page load
loadFullBP({ day: String(new Date().getDate()).padStart(2, "0"), month: new Date().toLocaleString("default", { month: "long" }) });

const newTaskForm = document.getElementById("new-task-form");
const taskInput = document.getElementById("task-input");

newTaskForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = taskInput.value.trim();
  if (!text) return;

  // Get current BP date from bpIndicator
  const currentBP = bpIndicator.textContent.replace("BattlePlan: ", "").trim();
  if (!currentBP) {
    toast("No active BattlePlan. Create one first.", "error");
    return;
  }

  try {
    const res = await fetch("/api/bps/task/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date: currentBP, text })
    });

    if (!res.ok) throw new Error("Failed to add task");
    const newTask = await res.json(); // { id: TASK_ID, text: "Task text", done: false }

    // Add the task to the DOM
    const li = document.createElement("li");
    li.className = "task-item";
    li.dataset.id = newTask.id;

    li.innerHTML = `
      <input type="checkbox" class="task-checkbox">
      <span class="task-text">${newTask.text}</span>
      <button class="delete-task-btn">Delete</button>
    `;

    // Hook checkbox toggle
    li.querySelector(".task-checkbox").addEventListener("change", async (e) => {
      const taskId = li.dataset.id;
      const state = e.target.checked;
      try {
        const res = await fetch("/api/bps/task/set_status", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ task_id: taskId, state })
        });
        if (!res.ok) throw new Error("Failed to update task status");
      } catch (err) {
        console.error(err);
        toast("Could not update task status. Reverting.", "error");
        e.target.checked = !state;
      }
    });

    // Hook delete button
    li.querySelector(".delete-task-btn").addEventListener("click", async () => {
      const taskId = li.dataset.id;
      try {
        const res = await fetch(`/api/bps/task/delete/${taskId}`, { method: "GET" });
        if (!res.ok) throw new Error("Failed to delete task");
        li.remove();
      } catch (err) {
        console.error(err);
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
