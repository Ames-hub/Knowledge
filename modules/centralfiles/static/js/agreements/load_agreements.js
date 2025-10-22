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

  async function deleteAgreement(cfid, agreementId) {
    try {
      const response = await fetch(`/api/files/${cfid}/agreements/delete`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          agreement_id: agreementId
        })
      });

      if (!response.ok) throw new Error("Failed to delete agreement");
      
      // Remove the row from the table
      const row = document.querySelector(`tr[data-agreement-id="${agreementId}"]`);
      if (row) {
        row.remove();
      }
      
      console.log(`Agreement ${agreementId} deleted`);
    } catch (err) {
      console.error("Error deleting agreement:", err);
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

        // Fulfilled checkbox cell
        const fulfilledCell = document.createElement("td");
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = agreement.fulfilled;

        checkbox.addEventListener("change", () => {
          const newValue = checkbox.checked;
          updateAgreement(FileCFID, agreement.agreement_id, newValue);
        });

        fulfilledCell.appendChild(checkbox);

        // Date cell
        const dateCell = document.createElement("td");
        dateCell.textContent = agreement.date;

        // Agreement text cell
        const textCell = document.createElement("td");
        textCell.textContent = agreement.agreement;

        // Delete button cell
        const deleteCell = document.createElement("td");
        const deleteButton = document.createElement("button");
        deleteButton.textContent = "Delete";
        deleteButton.className = "delete-agreement-btn";
        deleteButton.addEventListener("click", () => {
          if (confirm("Are you sure you want to delete this agreement?")) {
            deleteAgreement(FileCFID, agreement.agreement_id);
          }
        });
        deleteCell.appendChild(deleteButton);

        row.appendChild(fulfilledCell);
        row.appendChild(dateCell);
        row.appendChild(textCell);
        row.appendChild(deleteCell);

        table.appendChild(row);
      });
    } catch (err) {
      console.error("Error loading agreements:", err);
    }
  }

  loadAgreements();
});