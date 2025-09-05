const trackModal = document.getElementById('trackModal');
const payModal = document.getElementById('payModal');

document.getElementById('openTrackModal').onclick = () => trackModal.style.display = 'block';
document.getElementById('closeTrackModal').onclick = () => trackModal.style.display = 'none';

document.getElementById('openPayModal').onclick = () => payModal.style.display = 'block';
document.getElementById('closePayModal').onclick = () => payModal.style.display = 'none';

// Close modal if user clicks outside
window.onclick = function(event) {
    if (event.target == trackModal) trackModal.style.display = "none";
    if (event.target == payModal) payModal.style.display = "none";
}

// Handle Add Debt form
document.getElementById('trackDebtForm').onsubmit = async function(e) {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(this).entries());

    try {
        const res = await fetch("/api/finances/debts/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data) // includes description now
        });
        if (!res.ok) throw new Error(await res.text());

        console.log("Debt added:", data);
        alert("Debt successfully added!");
        this.reset();
        trackModal.style.display = 'none';
        loadDebts(); // refresh table after adding
    } catch (err) {
        console.error("Error adding debt:", err);
        alert("Failed to add debt.");
    }
}

// Handle Subtract Debt form
document.getElementById('payDebtForm').onsubmit = async function(e) {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(this).entries());

    try {
        const res = await fetch("/api/finances/debts/subtract", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error(await res.text());

        console.log("Debt subtracted:", data);
        alert("Payment successfully recorded!");
        this.reset();
        payModal.style.display = 'none';
        loadDebts(); // refresh table after payment
    } catch (err) {
        console.error("Error subtracting debt:", err);
        alert("Failed to record payment.");
    }
}

async function loadDebts() {
    try {
        const res = await fetch("/api/finances/debts/get_all", {
            headers: { "Content-Type": "application/json" }
        });
        if (!res.ok) throw new Error(await res.text());
        const debts = await res.json();

        const tbody = document.getElementById("debtsTableBody");
        tbody.innerHTML = ""; // clear existing

        Object.values(debts).forEach(debt => {
            const tr = document.createElement("tr");

            tr.innerHTML = `
                <td>${debt.debtor}</td>
                <td>${debt.debtee}</td>
                <td>${Number(debt.amount).toFixed(2)}</td>
                <td>${debt.start_date ?? "N/A"}</td>
                <td>${debt.end_date ?? "N/A"}</td>
                <td><span class="status ${getStatus(debt)}">${getStatus(debt)}</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Error loading debts:", err);
    }
}

function getStatus(debt) {
    if (!debt.end_date) return "pending";
    const due = new Date(debt.end_date);
    const now = new Date();
    return due < now ? "overdue" : "pending";
}

// load immediately on page load
window.addEventListener("DOMContentLoaded", loadDebts);

const debtorInput = document.querySelector('#payDebtForm input[name="debtor"]');
const debteeInput = document.querySelector('#payDebtForm input[name="debtee"]');
const recordSelect = document.getElementById('debtRecordSelect');

// helper: fetch and update dropdown
async function updateDebtRecords() {
    const debtor = debtorInput.value.trim();
    const debtee = debteeInput.value.trim();

    // only query if both filled
    if (!debtor || !debtee) {
        recordSelect.innerHTML = `<option value="">-- Select a debt record --</option>`;
        return;
    }

    try {
        const res = await fetch("/api/finances/debts/get_all_records", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ debtor, debtee })
        });
        if (!res.ok) {
            recordSelect.innerHTML = `<option value="">No records found</option>`;
            return;
        }
        const records = await res.json();

        // clear + repopulate
        recordSelect.innerHTML = "";
        const entries = Object.values(records);
        if (entries.length === 0) {
            recordSelect.innerHTML = `<option value="">No records found</option>`;
            return;
        }

        entries.forEach(record => {
            const option = document.createElement("option");
            option.value = record.record_id; // send back to backend
            option.textContent = `$${record.amount} (on ${record.start_date || "unknown"}) - ${record.description || "no description"}`;
            recordSelect.appendChild(option);
        });
    } catch (err) {
        console.error("Error fetching debt records:", err);
        recordSelect.innerHTML = `<option value="">Error loading records</option>`;
    }
}

// watch inputs as user types
debtorInput.addEventListener("input", updateDebtRecords);
debteeInput.addEventListener("input", updateDebtRecords);

// also refresh dropdown when modal opens (in case values already filled)
document.getElementById("openPayModal").addEventListener("click", updateDebtRecords);
