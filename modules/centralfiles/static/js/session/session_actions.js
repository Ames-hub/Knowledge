document.addEventListener("DOMContentLoaded", () => {
  const addActionBtn = document.getElementById("add-action-btn");
  const addActionForm = document.getElementById("add-action-form");
  const saveActionBtn = document.getElementById("save-action-btn");
  const cancelActionBtn = document.getElementById("cancel-action-btn");
  const newActionInput = document.getElementById("new-action-input");
  const actionsList = document.getElementById("actions-list");

  // --- Load actions from backend ---
  async function loadActions() {
    actionsList.innerHTML = "<p>Loading actions...</p>";

    try {
      const response = await fetch(`/api/files/get/${FileCFID}/sessions/${sessionId}/list_actions`);
      if (!response.ok) throw new Error("Failed to load actions.");

      const data = await response.json();
      actionsList.innerHTML = "";

      if (!data.actions || !data.actions.length) {
        actionsList.innerHTML = "<p>No planned actions found.</p>";
        return;
      }

      data.actions.forEach(renderAction);
    } catch (err) {
      console.error("Error loading actions:", err);
      actionsList.innerHTML = "<p>Could not load planned actions.</p>";
    }
  }

  // --- Render a single planned action ---
  function renderAction(action) {
    const item = document.createElement("div");
    item.classList.add("action-item");
    item.dataset.actionId = action.action_id;

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.classList.add("action-checkbox");
    checkbox.checked = !!action.completed;

    const label = document.createElement("label");
    label.classList.add("action-label");
    label.textContent = action.action_text;

    const deleteBtn = document.createElement("button");
    deleteBtn.classList.add("btn", "btn-danger", "btn-sm", "action-delete");
    deleteBtn.textContent = "✕";

    checkbox.addEventListener("change", () =>
      updateActionCompletion(action.action_id, checkbox.checked)
    );

    deleteBtn.addEventListener("click", () =>
      deleteAction(action.action_id, item)
    );

    item.append(checkbox, label, deleteBtn);
    actionsList.appendChild(item);
  }

  // --- Add new action ---
  addActionBtn.addEventListener("click", () => {
    addActionForm.style.display = "block";
    addActionBtn.disabled = true;
  });

  cancelActionBtn.addEventListener("click", () => {
    addActionForm.style.display = "none";
    addActionBtn.disabled = false;
    newActionInput.value = "";
  });

  saveActionBtn.addEventListener("click", async () => {
    const text = newActionInput.value.trim();
    if (!text) {
      alert("Please enter an action.");
      return;
    }

    const payload = { action_text: text };

    try {
      const response = await fetch(`/api/files/get/${FileCFID}/sessions/${sessionId}/add_action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error("Failed to add action.");
      const data = await response.json();

      // Expect backend to return { action_id: X }
      if (data.action_id) {
        renderAction({ action_id: data.action_id, action_text: text, completed: false });
      } else {
        await loadActions();
      }

      newActionInput.value = "";
      addActionForm.style.display = "none";
      addActionBtn.disabled = false;
    } catch (err) {
      console.error("Error adding action:", err);
      alert("Could not add planned action.");
    }
  });

  // --- Delete action ---
  async function deleteAction(actionId, element) {
    if (!confirm("Delete this planned action?")) return;

    try {
      const response = await fetch(`/api/files/get/${FileCFID}/sessions/${sessionId}/delete_action/${actionId}`, {
        method: "DELETE",
      });

      if (!response.ok) throw new Error("Failed to delete action.");
      element.remove();
    } catch (err) {
      console.error("Error deleting action:", err);
      alert("Could not delete action.");
    }
  }

  // --- Update completion state ---
  async function updateActionCompletion(actionId, completed) {
    try {
      const response = await fetch(`/api/files/get/${FileCFID}/sessions/${sessionId}/update_action/${actionId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ completed }),
      });

      if (!response.ok) throw new Error("Failed to update action completion.");
    } catch (err) {
      console.error("Error updating action completion:", err);
      alert("Could not update action status.");
    }
  }

  // Load all actions on page load
  loadActions();
});

const compBtn = document.getElementById("set-comp-btn")
compBtn.addEventListener("click", async () => {
  if (!confirm("Are you sure you want to mark this session as completed?")) return;

  try {
    const compResponse = await fetch(`/api/files/get/${FileCFID}/session/set_status/${sessionId}/1`, {
      method: "PUT",
    });

    if (!compResponse.ok) throw new Error("Failed to mark session as completed.");

    let status_type = document.getElementById("session_status")
    status_type.innerHTML = "completed"
    status_type.className = "session-status status-completed"

  } catch (err) {
    console.error(err);
    alert("Error completing session.");
  }
});

const setPendingBtn = document.getElementById("set-pending-btn")
setPendingBtn.addEventListener("click", async () => {
  if (!confirm("Are you sure you want to mark this session as pending/scheduled?")) return;

  try {
    const compResponse = await fetch(`/api/files/get/${FileCFID}/session/set_status/${sessionId}/2`, {
      method: "PUT",
    });

    if (!compResponse.ok) throw new Error("Failed to mark session as pending/scheduled.");

    let status_type = document.getElementById("session_status")
    status_type.innerHTML = "scheduled"
    status_type.className = "session-status status-scheduled"

  } catch (err) {
    console.error(err);
    alert("Error setting session as scheduled.");
  }
});

const cancelBtn = document.getElementById("set-cancelled-btn")
cancelBtn.addEventListener("click", async () => {
  if (!confirm("Are you sure you want to mark this session as cancelled?")) return;

  try {
    const compResponse = await fetch(`/api/files/get/${FileCFID}/session/set_status/${sessionId}/3`, {
      method: "PUT",
    });

    if (!compResponse.ok) throw new Error("Failed to mark session as cancelled.");

    let status_type = document.getElementById("session_status")
    status_type.innerHTML = "cancelled"
    status_type.className = "session-status status-cancelled"

  } catch (err) {
    console.error(err);
    alert("Error cancelling session.");
  }
});