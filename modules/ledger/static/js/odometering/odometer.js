// ------------------- API Helpers -------------------
async function loadFuelRate() {
  const res = await fetch("/api/ledger/odometer/fuel-rate");
  if (!res.ok) throw new Error("Failed to load fuel rate");
  const data = await res.json();
  return data.usage_ml;
}

async function setFuelRate(rate) {
  const res = await fetch("/api/ledger/odometer/fuel-rate", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ usage_ml: rate })
  });
  if (!res.ok) throw new Error("Failed to update fuel rate");

  const text = await res.text();
  if (text !== "ok") throw new Error("Failed to update fuel rate (server returned not ok)");
}

async function loadEntries() {
  const res = await fetch("/api/ledger/odometer/entries/read");
  if (!res.ok) throw new Error("Failed to load entries");
  const data = await res.json();
  return Object.values(data);
}

async function addEntryApi(entry) {
  const res = await fetch("/api/ledger/odometer/entries/write", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(entry)
  });
  if (!res.ok) throw new Error("Failed to add entry");

  const text = await res.text();
  if (text !== "ok") throw new Error("Failed to add entry (server returned not ok)");
  return true;
}

async function deleteEntryApi(entryId) {
  const res = await fetch(`/api/ledger/odometer/entries/delete/${entryId}`, {
    method: "DELETE"
  });
  if (!res.ok) throw new Error("Failed to delete entry");

  const text = await res.text();
  if (text !== "ok") throw new Error("Failed to delete entry (server returned not ok)");
}

// ------------------- Rendering -------------------
async function renderTable() {
  const tbody = document.getElementById("logTable");
  tbody.innerHTML = "";

  let entries;
  try {
    entries = await loadEntries();
  } catch (err) {
    console.error(err);
    tbody.innerHTML = `<tr><td colspan="5">Failed to load entries</td></tr>`;
    return;
  }

  // Sort by datetime ascending
  entries.sort((a, b) => new Date(a.datetime) - new Date(b.datetime));

  entries.forEach(entry => {
    const tr = document.createElement("tr");

    tr.innerHTML = `
      <td>${entry.datetime}</td>
      <td>${entry.odometer.toFixed(1)}</td>
      <td>${entry.distance_travelled.toFixed(1)}</td>
      <td>${entry.purpose}</td>
      <td>
        ${entry.fuel_used_ml.toFixed(0)} ml
        <span class="muted">(${(entry.fuel_used_ml / 1000).toFixed(2)} L)</span>
      </td>
      <td>
        <button class="delete-btn" data-id="${entry.entry_id}">Delete</button>
      </td>
    `;

    tbody.appendChild(tr);
  });

  // Attach delete handlers
  document.querySelectorAll(".delete-btn").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      const entryId = e.target.dataset.id;
      if (!confirm("Are you sure you want to delete this entry?")) return;
      try {
        await deleteEntryApi(entryId);
        await renderTable();
      } catch (err) {
        console.error(err);
        alert("Failed to delete entry.");
      }
    });
  });
}

// ------------------- Entry Form -------------------
async function addEntry() {
  const odoInput = document.getElementById("odometer");
  const purposeInput = document.getElementById("purpose");

  const odo = parseFloat(odoInput.value);
  const purpose = purposeInput.value.trim();

  if (isNaN(odo)) {
    alert("Please enter a valid odometer value.");
    return;
  }

  const payload = {
    date: new Date().toISOString(),
    odometer: odo,
    purpose: purpose
  };

  try {
    await addEntryApi(payload);
    await renderTable();
    odoInput.value = "";
    purposeInput.value = "";
  } catch (err) {
    console.error(err);
    alert("Failed to add entry.");
  }
}

// ------------------- Live Fuel Rate Update with Debounce -------------------
const fuelRateInput = document.getElementById("fuelRate");
let fuelRateTimeout;

fuelRateInput.addEventListener("input", () => {
  clearTimeout(fuelRateTimeout);
  fuelRateTimeout = setTimeout(async () => {
    const fuelRate = parseFloat(fuelRateInput.value);
    if (isNaN(fuelRate)) return; // Ignore invalid values

    try {
      await setFuelRate(fuelRate);
      console.log("Fuel rate updated:", fuelRate);
    } catch (err) {
      console.error(err);
      alert("Failed to update fuel rate.");
    }
  }, 500); // wait 500ms after last keystroke
});

// ------------------- Initialization -------------------
async function init() {
  try {
    const fuelRate = await loadFuelRate();
    document.getElementById("fuelRate").value = fuelRate;
    await renderTable();
  } catch (err) {
    console.error(err);
    alert("Failed to initialize odometer ledger.");
  }
}

// Attach add button
document.getElementById("addEntryBtn").addEventListener("click", addEntry);

// Start
init();
