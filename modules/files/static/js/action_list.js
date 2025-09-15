const form = document.getElementById("submit_action_form");
const input = document.getElementById("action_input");
const list = document.getElementById("action_list");
const cfidInput = document.getElementById("cfid_input");

// Load existing actions from DB
async function loadActions() {
  try {
    const response = await fetch(`/api/files/get_actions/${encodeURIComponent(cfidInput.value)}`);
    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const actions = await response.json(); // Expecting array of {id, action, date}
    list.innerHTML = ""; // clear current list

    actions.forEach(item => {
      const li = document.createElement("li");
      li.textContent = `${item.action} (${new Date(item.date).toLocaleString()})`;
      li.dataset.id = item.id; // keep ID if needed later
      list.appendChild(li);
    });
  } catch (err) {
    console.error("Failed to load actions:", err);
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const actionValue = input.value.trim();
  if (!actionValue) return;

  try {
    const response = await fetch("/api/files/submit_action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: actionValue, cfid: cfidInput.value })
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    // Load the new action
    loadActions()

    input.value = "";
  } catch (err) {
    console.error("Failed to submit action:", err);
    alert("Could not submit action. Please try again.");
  }
});

// Load actions when page loads
document.addEventListener("DOMContentLoaded", loadActions);