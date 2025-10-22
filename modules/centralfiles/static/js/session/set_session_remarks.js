document.addEventListener("DOMContentLoaded", () => {
  const remarksTextarea = document.getElementById("patient-remarks");
  const cfid = FileCFID;

  let debounceTimer;

  // Debounce function
  function debounceSave(func, delay = 500) {
    return function (...args) {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => func.apply(this, args), delay);
    };
  }

  // Function to send remarks to the backend
  async function saveRemarks() {
    const payload = {
      text_value: remarksTextarea.value
    };

    try {
      const response = await fetch(`/api/files/get/${cfid}/sessions/${sessionId}/set_remarks`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload)
      });

      const result = await response.json();

      if (!result.success) {
        console.error("Failed to save remarks:", result);
      }
    } catch (err) {
      console.error("Error saving remarks:", err);
    }
  }

  // Attach the debounced save to input events
  remarksTextarea.addEventListener("input", debounceSave(saveRemarks, 800));
});
