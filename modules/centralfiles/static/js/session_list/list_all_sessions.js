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
      card.innerHTML = `
        <div class="session-card-header">
          <div class="session-info">
            <h4 class="session-title">Session #${index + 1}</h4>
            <div class="session-meta">
              <span class="session-date">${session.date}</span>
              <span class="session-duration">${session.duration} minutes</span>
            </div>
          </div>
          <div class="session-status status-completed">
            Completed
          </div>
        </div>

        <div class="session-card-body">
          <p class="session-summary">${session.summary}</p>
          <div class="session-actions">
            <button class="btn btn-sm btn-secondary view-btn" data-id="${session.session_id}">👁️ View Details</button>
            <button class="btn btn-sm btn-danger delete-btn" data-id="${session.session_id}">🗑️ Delete</button>
          </div>
        </div>
      `;
      container.appendChild(card);

      // Add event listeners
      const viewBtn = card.querySelector(".view-btn");
      const deleteBtn = card.querySelector(".delete-btn");

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
    });

  } catch (err) {
    console.error(err);
    container.innerHTML = `<p style="color:red;">Error loading sessions.</p>`;
  }
}

document.addEventListener("DOMContentLoaded", loadSessions);
