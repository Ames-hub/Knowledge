// controls.js
document.addEventListener("DOMContentLoaded", function() {
  // Clear BP button
  const clearBtn = document.getElementById("clear-btn");
  clearBtn.addEventListener("click", async () => {
    if (!currentBPId) return;
    try {
      const res = await fetch("/api/bps/clear", { 
        method: "POST", 
        headers: { "Content-Type": "application/json" }, 
        body: JSON.stringify({ date: currentBPDate }) 
      });
      if (!res.ok) throw new Error("Failed to clear BP");

      taskList.innerHTML = "";
      await loadQuotas(currentBPId);
      await updateQuotaStatus(currentBPId);
      if (doNotifySuccess) toast("Battle Plan cleared", "success");
    } catch {
      toast("Failed to clear BP", "error");
    }
  });

  // Import yesterday's BP button
  const importBtn = document.getElementById("import-btn");
  importBtn.addEventListener("click", async () => {
    if (!currentBPId) return;
    try {
      const res = await fetch("/api/bps/yesterday_import", { 
        method: "POST", 
        headers: { "Content-Type": "application/json" }, 
        body: JSON.stringify({ date_today: currentBPDate }) 
      });
      if (!res.ok) throw new Error("Failed to import yesterday's BP");
      const [day, month] = currentBPDate.split("-");
      await loadFullBP({ day, month });
      if (doNotifySuccess) toast("Yesterday's BP imported", "success");
    } catch {
      toast("Failed to import yesterday's BP", "error");
    }
  });

  // Help button
  const helpBtn = document.getElementById("help-btn");
  const helpModal = document.getElementById("bp-help-modal");
  const helpClose = document.getElementById("bp-help-close");
  
  helpBtn.addEventListener("click", () => helpModal.classList.remove("hidden"));
  helpClose.addEventListener("click", () => helpModal.classList.add("hidden"));

  // Add Quota button
  const addQuotaBtn = document.getElementById('add-quota-btn');
  const addQuotaModal = document.getElementById('add-quota-modal');
  const addQuotaCancel = document.getElementById('add-quota-cancel');
  const addQuotaForm = document.getElementById('add-quota-form');

  addQuotaBtn.addEventListener('click', () => {
    addQuotaModal.classList.remove('hidden');
    document.getElementById('new-quota-name').focus();
  });

  addQuotaCancel.addEventListener('click', () => {
    addQuotaModal.classList.add('hidden');
  });

  addQuotaForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('new-quota-name').value.trim();

    if(!name) return;

    try {
      const res = await fetch('/api/bps/quota/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          "bp_id": currentBPId,
          "quota_name": name,
        })
      });

      if(!res.ok) throw new Error('Failed to create quota');

      addQuotaForm.reset();
      addQuotaModal.classList.add('hidden');
      await loadQuotas(currentBPId, currentBPDate);
    } catch (err) {
      console.error(err);
      toast('Error creating quota on server.', 'error');
    }
  });

  // Delete Quota button
  const deleteQuotaBtn = document.getElementById('delete-quota-btn');
  const deleteQuotaModal = document.getElementById('delete-quota-modal');
  const deleteQuotaCancel = document.getElementById('delete-quota-cancel');
  const deleteQuotaForm = document.getElementById('delete-quota-form');
  const quotaToDeleteSelect = document.getElementById('quota-to-delete');

  deleteQuotaBtn.addEventListener('click', async () => {
    if (!currentBPId) return toast("No active BattlePlan", "error");

    try {
      const res = await fetch(`/api/bps/quota/list/${encodeURIComponent(currentBPDate)}`);
      if (!res.ok) throw new Error("Failed to fetch quotas");
      const quotas = await res.json();

      quotaToDeleteSelect.innerHTML = "";
      quotas.forEach(q => {
        const option = document.createElement("option");
        option.value = q.quota_id;
        option.textContent = q.name;
        quotaToDeleteSelect.appendChild(option);
      });

      deleteQuotaModal.classList.remove('hidden');
      quotaToDeleteSelect.focus();
    } catch (err) {
      console.error(err);
      toast("Failed to load quotas", "error");
    }
  });

  deleteQuotaCancel.addEventListener('click', () => {
    deleteQuotaModal.classList.add('hidden');
  });

  deleteQuotaForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const quotaId = quotaToDeleteSelect.value;
    if (!quotaId) return;

    try {
      const res = await fetch('/api/bps/quota/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quota_id: quotaId })
      });

      if (!res.ok) throw new Error('Failed to delete quota');

      toast("Quota deleted", "success");
      deleteQuotaModal.classList.add('hidden');
      await loadQuotas(currentBPId, currentBPDate);
    } catch (err) {
      console.error(err);
      toast("Failed to delete quota", "error");
    }
  });
});