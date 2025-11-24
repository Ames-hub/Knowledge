async function loadSessions() {
  const container = document.getElementById("sessionsContainer");
  container.innerHTML = "<p>Loading sessions...</p>";

  try {
    const response = await fetch(`/api/files/get/${FileCFID}/sessions/list_all`);
    if (!response.ok) throw new Error("Failed to fetch sessions.");

    const sessions = await response.json();

    container.innerHTML = ""; // Clear placeholder

    if (!sessions.length) {
      container.innerHTML = "<p>No sessions found.</p>";
      return;
    }

    sessions.forEach((session, index) => {
      const card = document.createElement("div");
      card.className = "session-card";
      
      if (session.status_code === 1) {
        compType = "completed"
      }
      else if (session.status_code === 2) {
        compType = "pending"
      } 
      else if (session.status_code === 3) {
        compType = "cancelled"
      } 

      card.innerHTML = `
        <div class="session-card-header">
          <div class="session-info">
            <h4 class="session-title">Session #${index + 1}</h4>
            <div class="session-meta">
              <span class="session-date">${session.date}</span>
              <span class="session-duration">${session.duration} minutes</span>
            </div>
          </div>
          <div id="session_${session.session_id}_status" class="session-status status-${compType}">
            ${compType}
          </div>
        </div>

        <div class="session-card-body">
          <p class="session-summary">${session.summary}</p>
          <div class="session-actions-left">
            <button class="btn btn-sm btn-secondary view-btn" data-id="${session.session_id}">👁️ View Details</button>
            <button class="btn btn-sm btn-danger delete-btn" data-id="${session.session_id}">🗑️ Delete</button>
          </div>
          <div class="session-actions-right">
            <button class="btn btn-sm btn-primary set-comp-btn" data-id="${session.session_id}">Mark Done</button>
            <button class="btn btn-sm btn-secondary set-pending-btn" data-id="${session.session_id}">Set Pending</button>
            <button class="btn btn-sm btn-danger set-cancelled-btn" data-id="${session.session_id}">Cancel Session</button>
          </div>
        </div>
      `;
      container.appendChild(card);

      // Add event listeners
      const viewBtn = card.querySelector(".view-btn");
      const deleteBtn = card.querySelector(".delete-btn");
      const compBtn = card.querySelector(".set-comp-btn")
      const setPendingBtn = card.querySelector(".set-pending-btn")
      const cancelBtn = card.querySelector(".set-cancelled-btn")

      viewBtn.addEventListener("click", () => {
        window.location.href = `/files/get/${FileCFID}/sessions/${session.session_id}`;
      });

      deleteBtn.addEventListener("click", async () => {
        if (!confirm("Are you sure you want to delete this session?")) return;

        try {
          const deleteResponse = await fetch(`/api/files/get/${FileCFID}/delete/session/${session.session_id}`, {
            method: "DELETE",
          });

          if (!deleteResponse.ok) throw new Error("Failed to delete session.");

          // Remove card from DOM
          card.remove();
        } catch (err) {
          console.error(err);
          alert("Error deleting session.");
        }
      });

      compBtn.addEventListener("click", async () => {
        if (!confirm("Are you sure you want to mark this session as completed?")) return;

        try {
          const compResponse = await fetch(`/api/files/get/${FileCFID}/session/set_status/${session.session_id}/1`, {
            method: "PUT",
          });

          if (!compResponse.ok) throw new Error("Failed to mark session as completed.");

          let status_type = document.getElementById(`session_${session.session_id}_status`)
          status_type.innerHTML = "completed"
          status_type.className = "session-status status-completed"

        } catch (err) {
          console.error(err);
          alert("Error completing session.");
        }
      });

      setPendingBtn.addEventListener("click", async () => {
        if (!confirm("Are you sure you want to mark this session as pending/scheduled?")) return;

        try {
          const compResponse = await fetch(`/api/files/get/${FileCFID}/session/set_status/${session.session_id}/2`, {
            method: "PUT",
          });

          if (!compResponse.ok) throw new Error("Failed to mark session as pending/scheduled.");

          let status_type = document.getElementById(`session_${session.session_id}_status`)
          status_type.innerHTML = "scheduled"
          status_type.className = "session-status status-scheduled"

        } catch (err) {
          console.error(err);
          alert("Error setting session as scheduled.");
        }
      });

      cancelBtn.addEventListener("click", async () => {
        if (!confirm("Are you sure you want to mark this session as cancelled?")) return;

        try {
          const compResponse = await fetch(`/api/files/get/${FileCFID}/session/set_status/${session.session_id}/3`, {
            method: "PUT",
          });

          if (!compResponse.ok) throw new Error("Failed to mark session as cancelled.");

          let status_type = document.getElementById(`session_${session.session_id}_status`)
          status_type.innerHTML = "cancelled"
          status_type.className = "session-status status-cancelled"

        } catch (err) {
          console.error(err);
          alert("Error cancelling session.");
        }
      });
    });


  } catch (err) {
    console.error(err);
    container.innerHTML = `<p style="color:red;">Error loading sessions.</p>`;
  }
}

document.addEventListener("DOMContentLoaded", loadSessions);
