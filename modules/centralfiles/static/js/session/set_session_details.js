document.addEventListener("DOMContentLoaded", () => {
  const cfid = FileCFID;

  const dateInput = document.getElementById("session-date");
  const durationInput = document.getElementById("session-duration");
  const auditorInput = document.getElementById("session-auditor");
  const summaryInput = document.getElementById("session-summary");

  // Function to save session details
  async function saveSessionDetails() {
    const payload = {
      date: dateInput.value,
      duration: parseInt(durationInput.value) || 0,
      auditor: auditorInput.value,
      summary: summaryInput.value
    };

    try {
      const response = await fetch(`/files/get/${cfid}/sessions/${sessionId}/set_details`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload)
      });

      const result = await response.json();

      if (result.success) {
        alert("Session details saved successfully!");
      } else {
        alert("Failed to save session details.");
      }
    } catch (err) {
      console.error("Error saving session:", err);
      alert("An error occurred while saving session details.");
    }
  }

  // You can bind this to a button or auto-save on input change
  const saveBtn = document.createElement("button");
  saveBtn.textContent = "Save Session";
  saveBtn.className = "btn btn-primary";
  saveBtn.addEventListener("click", saveSessionDetails);
  document.querySelector(".session-info").appendChild(saveBtn);
});
