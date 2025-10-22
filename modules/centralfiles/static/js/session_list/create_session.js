document.addEventListener("DOMContentLoaded", () => {
  const addSessionBtn = document.getElementById("add-session-btn");

  if (!addSessionBtn) return;

  addSessionBtn.addEventListener("click", async () => {
    try {
      // Get current CFID from global
      if (typeof FileCFID === "undefined") {
        console.error("CFID not found in global scope.");
        return;
      }

      // Format today's date as YYYY-MM-DD
      const today = new Date().toISOString().split("T")[0];

      // Construct endpoint
      const endpoint = `/api/files/get/${FileCFID}/sessions/create/${today}`;
      console.log(`Creating session for CFID ${FileCFID} on ${today}`);

      // Call backend
      const response = await fetch(endpoint);
      if (!response.ok) throw new Error(`Request failed: ${response.status}`);

      const newSessionId = await response.text();

      console.log(`✅ Session created successfully. ID: ${newSessionId}`);

      loadSessions();

    } catch (err) {
      console.error("Error creating session:", err);
      alert("Failed to create new session. Check console for details.");
    }
  });
});
