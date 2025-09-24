const quotaList = document.getElementById("quota-list");
const debouncedSaveNeeded = debounce((quotaId, v) => saveQuota("needed", quotaId, v), 700);
const debouncedSaveDone = debounce((quotaId, v) => saveQuota("done", quotaId, v), 700);

async function loadQuotas(bpId, bpDate = currentBPDate) {
  if (!bpId || !bpDate) return;
  try {
    const res = await fetch(`/api/bps/quota/list/${encodeURIComponent(bpDate)}`);
    if (!res.ok) throw new Error("Failed to load quotas");
    const quotas = await res.json();

    quotaList.innerHTML = "";
    quotas.forEach(quota => {
      const row = document.createElement("div");
      row.className = "quota-row";
      row.dataset.quotaId = quota.quota_id;

      row.innerHTML = `
        <span class="quota-name">${quota.name}</span>
        <input type="number" class="quota-done" value="${quota.done_amount || 0}" min="0"> /
        <input type="number" class="quota-needed" value="${quota.planned_amount || 0}" min="0">
      `;

      const neededInput = row.querySelector(".quota-needed");
      const doneInput = row.querySelector(".quota-done");

      neededInput.addEventListener("input", e => {
        const val = parseFloat(e.target.value);
        if (!isNaN(val)) debouncedSaveNeeded(quota.quota_id, val);
      });

      doneInput.addEventListener("input", e => {
        const val = parseFloat(e.target.value);
        if (!isNaN(val)) debouncedSaveDone(quota.quota_id, val);
      });

      quotaList.appendChild(row);
    });
  } catch (err) {
    console.error(err);
    toast("Failed to load quota info", "error");
  }
}

async function saveQuota(type, quotaId, value) {
  if (!currentBPId) return;
  let url, payload;

  if (type === "needed") {
    url = "/api/bps/quota/wanted/set";
    payload = { quota_id: quotaId, amount: value };
  } else {
    url = "/api/bps/quota/done/set";
    payload = { quota_id: quotaId, amount: value };
  }

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`Failed to save quota ${type}`);
    await updateQuotaStatus(currentBPId);
    if (doNotifySuccess) toast(`Quota ${type} saved`, "success");
  } catch (err) {
    console.error(err);
    toast(`Failed to save quota ${type}`, "error");
  }
}

async function updateQuotaStatus(bpId, bpDate = currentBPDate) {
  if (!bpId) return;
  try {
    const res = await fetch("/api/bps/quota/weekly", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date: bpDate })
    });

    if (!res.ok) return;

    const weekly = await res.json();
    const totalsForBp = weekly.weekly_totals?.[bpId];

    // Find the quota row container for this bpId
    const quotaRow = document.querySelector(`.quota-row[data-bp-id="${bpId}"]`);
    if (!quotaRow) return;

    // Remove old breakdown if it exists
    const oldBreakdown = quotaRow.querySelector(".weekly-breakdown");
    if (oldBreakdown) oldBreakdown.remove();

    if (totalsForBp && Object.keys(totalsForBp).length > 0) {
      // Create a new breakdown element
      const breakdownDiv = document.createElement("div");
      breakdownDiv.className = "weekly-breakdown";

      for (const [statName, total] of Object.entries(totalsForBp)) {
        const statEl = document.createElement("span");
        statEl.className = "weekly-stat";
        statEl.textContent = `${statName}: ${total}`;
        breakdownDiv.appendChild(statEl);
      }

      quotaRow.appendChild(breakdownDiv);
    }
  } catch (err) {
    console.error("Error fetching weekly production:", err);
  }
}