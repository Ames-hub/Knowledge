document.addEventListener("DOMContentLoaded", () => {
  const engramList = document.getElementById("engrams-list");

  async function loadEngrams() {
    engramList.innerHTML = "<p>Loading engrams...</p>";

    try {
      const response = await fetch(`/api/files/get/${FileCFID}/sessions/${sessionId}/list_engrams`);
      if (!response.ok) throw new Error("Failed to fetch engrams.");

      const data = await response.json();
      if (!data.success || !Array.isArray(data.engrams)) {
        throw new Error("Invalid response from server.");
      }

      // Clear any existing items
      engramList.innerHTML = "";

      if (data.engrams.length === 0) {
        engramList.innerHTML = "<p class='no-data'>No engrams recorded for this session yet.</p>";
        return;
      }

      // Populate engrams
      for (const e of data.engrams) {
        const item = document.createElement("div");
        item.classList.add("engram-item");

        const content = document.createElement("div");
        content.classList.add("engram-content");

        const actions = document.createElement("div");
        actions.innerHTML = `<strong>Actions:</strong> ${e.actions || "—"}`;
        const incident = document.createElement("div");
        incident.innerHTML = `<strong>Incident:</strong> ${e.incident || "—"}`;
        const somatic = document.createElement("div");
        somatic.innerHTML = `<strong>Somatic:</strong> ${e.somatic || "—"}`;
        const age = document.createElement("div");
        age.innerHTML = `<strong>Age:</strong> ${e.incident_age || "—"}`;

        content.append(actions, incident, somatic, age);

        const deleteBtn = document.createElement("button");
        deleteBtn.classList.add("btn", "btn-danger", "btn-sm", "engram-delete");
        deleteBtn.textContent = "✕";

        deleteBtn.addEventListener("click", async () => {
          // Optional: Add backend delete here later
          item.remove();
        });

        item.append(content, deleteBtn);
        engramList.appendChild(item);
      }
    } catch (err) {
      console.error("Error loading engrams:", err);
      engramList.innerHTML = "<p class='error'>Failed to load engrams.</p>";
    }
  }

  // Load engrams immediately when the page loads
  loadEngrams();
});