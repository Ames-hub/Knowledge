// Handle click on "submit" buttons in incoming/outgoing
document.addEventListener("click", (e) => {
  if (e.target.matches(".incoming button, .outgoing button")) {
    e.preventDefault();
    const modal = document.getElementById("transactionModal");
    modal.style.display = "flex";

    // Store type + account for later use
    const type = e.target.dataset.type;
    const accountId = e.target.dataset.account;
    modal.dataset.type = type;
    modal.dataset.accountId = accountId;

    // Update modal title
    const title = modal.querySelector("h3");
    title.textContent = type === "incoming" ? "Inflow Transaction" : "Expenses Transaction";

    // Grab the amount from the corresponding input box
    const accountRow = e.target.closest(".account-row");
    const amountInput = accountRow.querySelector(
      type === "incoming" ? ".incoming input" : ".outgoing input"
    );
    const amount = amountInput.value.trim() || "0.00";

    // Update the modal’s little text field
    const moneyText = modal.querySelector("#moneyText");
    moneyText.textContent = "Amount: $" + amount;

    // Also store amount in modal (so saveBtn can access it)
    modal.dataset.amount = amount;
  }
});

// Close modal (cancel)
document.getElementById("cancelBtn").addEventListener("click", () => {
  const modal = document.getElementById("transactionModal");
  modal.style.display = "none";
  document.getElementById("transactionDesc").value = "";
});

// Save transaction
document.getElementById("saveBtn").addEventListener("click", async () => {
  const modal = document.getElementById("transactionModal");
  const desc = document.getElementById("transactionDesc").value.trim();
  const type = modal.dataset.type; // "incoming" or "outgoing"
  const accountId = modal.dataset.accountId;
  const amount = modal.dataset.amount || "0.00";

  if (!desc) {
    alert("Please enter a description.");
    return;
  }

  if (parseFloat(amount) <= 0) {
    alert("Please enter an amount greater than zero.");
    return;
  }

  try {
    // Send to backend for persistence
    const response = await fetch("/api/finances/modify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account_id: parseInt(accountId),
        amount: parseFloat(amount),
        description: desc,
        is_expense: type === "outgoing"
      })
    });

    if (!response.ok) throw await response.json();

    // If successful, add transaction visually too
    const accountRow = document.querySelector(
      `.account-row .incoming button[data-account="${accountId}"]`
    ).closest(".account-row");

    const list = accountRow.querySelector(
      type === "incoming" ? ".incoming-list ul" : ".outgoing-list ul"
    );

    const li = document.createElement("li");
    li.textContent = `${type === "incoming" ? "+ " : "- "}$${amount} — ${desc}`;
    list.appendChild(li);

    // Reset inputs
    const amountInput = accountRow.querySelector(
      type === "incoming" ? ".incoming input" : ".outgoing input"
    );
    amountInput.value = "";
    document.getElementById("transactionDesc").value = "";

    // Optionally refresh account balances
    if (typeof loadAccounts === "function") {
      loadAccounts();
    }

    alert("Transaction saved!");
  } catch (err) {
    console.error(err);
    alert("Error saving transaction: " + (err.message || "Something went wrong."));
  }

  // Close modal
  modal.style.display = "none";
});

// Preset buttons: auto-fill description
document.querySelectorAll(".preset-options button").forEach(btn => {
  btn.addEventListener("click", () => {
    document.getElementById("transactionDesc").value = btn.dataset.value;
  });
});


// ============================
// Account create/delete modal
// ============================

// Open modal
document.getElementById("openAccountModal").addEventListener("click", () => {
  const modal = document.getElementById("accountModal");

  // Reset everything fresh so browser can't cache state
  const actionSelect = document.getElementById("accountAction");
  actionSelect.value = "create"; // force default
  document.getElementById("newAccountName").value = "";
  document.getElementById("deleteAccountSelect").innerHTML = "";
  document.getElementById("deleteAccountSelect").disabled = true;

  document.getElementById("accountModalTitle").textContent = "Create New Account";
  document.getElementById("createFields").style.display = "block";
  document.getElementById("deleteFields").style.display = "none";

  // Ensure no autocomplete
  actionSelect.setAttribute("autocomplete", "off");
  document.getElementById("newAccountName").setAttribute("autocomplete", "off");
  document.getElementById("deleteAccountSelect").setAttribute("autocomplete", "off");

  modal.style.display = "flex";
});

// Cancel
document.getElementById("accountCancel").addEventListener("click", () => {
  document.getElementById("accountModal").style.display = "none";
  document.getElementById("newAccountName").value = "";
});

// Switch between create/delete fields
document.getElementById("accountAction").addEventListener("change", (e) => {
  const mode = e.target.value;
  document.getElementById("accountModalTitle").textContent =
    mode === "create" ? "Create New Account" : "Delete Account";

  document.getElementById("createFields").style.display =
    mode === "create" ? "block" : "none";
  document.getElementById("deleteFields").style.display =
    mode === "delete" ? "block" : "none";

  if (mode === "delete") {
    document.getElementById("deleteAccountSelect").disabled = false;
    populateDeleteDropdown();
  } else {
    document.getElementById("deleteAccountSelect").disabled = true;
    document.getElementById("deleteAccountSelect").innerHTML = "";
  }
});

// Confirm button
document.getElementById("accountConfirm").addEventListener("click", async () => {
  const mode = document.getElementById("accountAction").value;

  try {
    if (mode === "create") {
      const accountName = document.getElementById("newAccountName").value.trim();
      if (!accountName) {
        alert("Please enter an account name.");
        return;
      }

      const response = await fetch("/api/finances/account/make", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ account_name: accountName })
      });

      if (!response.ok) throw await response.json();
      alert("Account created!");
    } else {
      const accountId = document.getElementById("deleteAccountSelect").value;
      if (!accountId) {
        alert("Please select an account to delete.");
        return;
      }

      const response = await fetch(`/api/finances/account/delete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ account_id: accountId })
      });

      if (!response.ok) throw await response.json();
      alert("Account deleted!");
    }

    // Close modal + refresh accounts
    document.getElementById("accountModal").style.display = "none";
    document.getElementById("newAccountName").value = "";
    loadAccounts();

  } catch (err) {
    console.error(err);
    alert("Error: " + (err.message || "Something went wrong."));
  }
});

// Populate delete dropdown with live accounts
async function populateDeleteDropdown() {
  try {
    const response = await fetch("/api/finances/load_accounts");
    if (!response.ok) return;

    const accounts = await response.json();
    const select = document.getElementById("deleteAccountSelect");
    select.innerHTML = "";

    accounts.forEach(acc => {
      const opt = document.createElement("option");
      opt.value = acc.account_id;
      opt.textContent = `${acc.account_name} (Balance: $${acc.balance})`;
      select.appendChild(opt);
    });
  } catch (err) {
    console.error("Failed to load accounts for deletion", err);
  }
}
