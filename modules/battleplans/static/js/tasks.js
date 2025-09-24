const taskList = document.getElementById("task-list");
const newTaskForm = document.getElementById("new-task-form");
const taskInput = document.getElementById("task-input");
const taskCategory = document.getElementById("task-category");

newTaskForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!(await ensureEditAllowed(taskInput))) return;

  const text = taskInput.value.trim();
  const category = taskCategory.value;
  if (!text || !currentBPId) return toast("No active BattlePlan. Create one first.", "error");

  try {
    const res = await fetch("/api/bps/task/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ "date": currentBPDate, "text": text, "category": category })
    });
    if (!res.ok) throw new Error("Failed to add task");
    const newTask = await res.json();

    const li = document.createElement("li");
    li.className = "task-item";
    li.dataset.id = newTask.id;
    li.innerHTML = `
      <input type="checkbox" class="task-checkbox">
      <span class="task-text">${newTask.text}</span>
      <span class="task-category">[${category}]</span>
      <button class="delete-task-btn">Delete</button>
    `;
    taskList.appendChild(li);
    taskInput.value = "";
    taskCategory.value = "work";

    // Event listeners
    li.querySelector(".task-checkbox").addEventListener("change", async (e) => {
      if (!(await ensureEditAllowed(e.target))) return;
      const taskId = li.dataset.id;
      const state = e.target.checked;
      try {
        const r = await fetch("/api/bps/task/set_status", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ task_id: taskId, state }) });
        if (!r.ok) throw new Error();
        if (doNotifySuccess) toast("Task status updated", "success");
      } catch { e.target.checked = !state; toast("Could not update task status. Reverting.", "error"); }
    });

    li.querySelector(".delete-task-btn").addEventListener("click", async () => {
      if (!(await ensureEditAllowed(li.querySelector(".delete-task-btn")))) return;
      const taskId = li.dataset.id;
      try {
        const r = await fetch(`/api/bps/task/delete/${taskId}`, { method: "GET" });
        if (!r.ok) throw new Error();
        li.remove();
        if (doNotifySuccess) toast("Task deleted", "success");
      } catch { toast("Failed to delete task. Try again.", "error"); }
    });

  } catch (err) { console.error(err); toast("Failed to add new task.", "error"); }
});
