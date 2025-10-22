document.addEventListener("DOMContentLoaded", () => {
  const table = document.querySelector(".left-column .card table");

  function clearTable() {
    const rows = table.querySelectorAll("tr");
    rows.forEach((row, index) => {
      if(index !== 0) row.remove();
    });
  }

  async function updateAgreement(cfid, agreementId, value) {
    try {
      const response = await fetch(`/api/files/${cfid}/agreements/set`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          agreement_id: agreementId,
          value: value
        })
      });

      if (!response.ok) throw new Error("Failed to update agreement");
      console.log(`Agreement ${agreementId} updated: ${value}`);
    } catch (err) {
      console.error("Error updating agreement:", err);
    }
  }

  async function loadAgreements() {
    try {
      const response = await fetch(`/api/files/${FileCFID}/agreements/get`, {method: "GET"});
      if (!response.ok) throw new Error("Failed to fetch agreements");
      const agreements = await response.json();

      clearTable();

      agreements.forEach(agreement => {
        const row = document.createElement("tr");
        row.dataset.agreementId = agreement.agreement_id;

        const fulfilledCell = document.createElement("td");
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = agreement.fulfilled;

        // Add listener to send update when toggled
        checkbox.addEventListener("change", () => {
          const newValue = checkbox.checked;
          updateAgreement(FileCFID, agreement.agreement_id, newValue);
        });

        fulfilledCell.appendChild(checkbox);

        const dateCell = document.createElement("td");
        dateCell.textContent = agreement.date;

        const textCell = document.createElement("td");
        textCell.textContent = agreement.agreement;

        row.appendChild(fulfilledCell);
        row.appendChild(dateCell);
        row.appendChild(textCell);

        table.appendChild(row);
      });
    } catch (err) {
      console.error("Error loading agreements:", err);
    }
  }

  loadAgreements();
});
