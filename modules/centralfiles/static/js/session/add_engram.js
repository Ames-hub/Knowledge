document.addEventListener("DOMContentLoaded", () => {
  const addEngramBtn = document.getElementById("add-engram-btn");
  const addEngramForm = document.getElementById("add-engram-form");
  const saveEngramBtn = document.getElementById("save-engram-btn");
  const cancelEngramBtn = document.getElementById("cancel-engram-btn");

  const actionsInput = document.getElementById("new-engram-actions");
  const incidentInput = document.getElementById("new-engram-incident");
  const somaticInput = document.getElementById("new-engram-somatic");
  const ageInput = document.getElementById("new-engram-age");
  const engramList = document.getElementById("engrams-list");

  // --- Load engrams from backend ---
  async function loadEngrams() {
    engramList.innerHTML = "<p>Loading engrams...</p>";

    try {
      const response = await fetch(`/api/files/get/${FileCFID}/sessions/${sessionId}/list_engrams`);
      if (!response.ok) throw new Error("Failed to fetch engrams.");

      const data = await response.json();
      engramList.innerHTML = "";

      if (!data.engrams || !data.engrams.length) {
        engramList.innerHTML = "<p>No engrams found.</p>";
        return;
      }

      data.engrams.forEach(renderEngram);
    } catch (err) {
      console.error("Error loading engrams:", err);
      engramList.innerHTML = "<p>Could not load engrams.</p>";
    }
  }

  // --- Render a single engram element ---
  function renderEngram(engram) {
    const newEngram = document.createElement("div");
    newEngram.classList.add("engram-item");
    newEngram.dataset.engramId = engram.engram_id;

    const contentDiv = document.createElement("div");
    contentDiv.classList.add("engram-content");

    contentDiv.innerHTML = `
      <div><strong>Actions:</strong> ${engram.actions}</div>
      <div><strong>Incident:</strong> ${engram.incident}</div>
      <div><strong>Somatic:</strong> ${engram.somatic}</div>
      <div><strong>Age:</strong> ${engram.incident_age}</div>
    `;

    const deleteBtn = document.createElement("button");
    deleteBtn.classList.add("btn", "btn-danger", "btn-sm", "engram-delete");
    deleteBtn.textContent = "✕";
    deleteBtn.addEventListener("click", () => deleteEngram(engram.engram_id, newEngram));

    newEngram.append(contentDiv, deleteBtn);
    engramList.appendChild(newEngram);
  }

  // --- Delete engram from backend ---
  async function deleteEngram(engramId, element) {
    if (!confirm("Are you sure you want to delete this engram?")) return;

    try {
      const response = await fetch(`/api/files/get/${FileCFID}/sessions/${sessionId}/delete_engram/${engramId}`, {
        method: "DELETE"
      });

      if (!response.ok) throw new Error("Failed to delete engram.");

      element.remove();
    } catch (err) {
      console.error("Error deleting engram:", err);
      alert("Could not delete engram.");
    }
  }

  // --- Add a new engram ---
  addEngramBtn.addEventListener("click", () => {
    addEngramForm.style.display = "block";
    addEngramBtn.disabled = true;
  });

  cancelEngramBtn.addEventListener("click", () => {
    addEngramForm.style.display = "none";
    addEngramBtn.disabled = false;
    actionsInput.value = "";
    incidentInput.value = "";
    somaticInput.value = "";
    ageInput.value = "";
  });

  saveEngramBtn.addEventListener("click", async () => {
    const actions = actionsInput.value.trim();
    const incident = incidentInput.value.trim();
    const somatic = somaticInput.value.trim();
    const age = ageInput.value.trim();

    if (!actions || !incident || !somatic || !age) {
      alert("All fields are required.");
      return;
    }

    const payload = {
      actions,
      incident,
      somatic,
      incident_age: age
    };

    try {
      const response = await fetch(`/api/files/get/${FileCFID}/sessions/${sessionId}/add_engram`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok) throw new Error("Failed to add engram.");
      const data = await response.json();

      if (data.engram_id) {
        // Backend should return the ID of the created engram
        renderEngram({
          engram_id: data.engram_id,
          actions,
          incident,
          somatic,
          incident_age: age
        });
      } else {
        // Fallback if backend doesn’t return it
        await loadEngrams();
      }

      actionsInput.value = "";
      incidentInput.value = "";
      somaticInput.value = "";
      ageInput.value = "";
      addEngramForm.style.display = "none";
      addEngramBtn.disabled = false;
    } catch (err) {
      console.error(err);
      alert("Could not add engram. See console for details.");
    }
  });

  // Load existing engrams on page load
  loadEngrams();
});
