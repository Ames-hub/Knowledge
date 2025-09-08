document.addEventListener("DOMContentLoaded", () => {
  loadAccounts();

  // View Transaction Modal Buttons
  const viewCancelBtn = document.getElementById("viewCancelBtn");
  const viewDeleteBtn = document.getElementById("viewDeleteBtn");

  viewCancelBtn?.addEventListener("click", () => {
    const modal = document.getElementById("viewTransactionModal");
    const receiptContainer = document.getElementById("viewReceiptContainer");
    if (modal) modal.style.display = "none";
    if (receiptContainer) receiptContainer.innerHTML = "";
  });

  viewDeleteBtn?.addEventListener("click", async () => {
    const modal = document.getElementById("viewTransactionModal");
    if (!modal) return;
    const txnId = modal.dataset.txnId;
    try {
      const res = await fetch("/api/finances/del_transaction", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transaction_id: txnId })
      });
      if (!res.ok) throw await res.json();
      modal.style.display = "none";
      loadAccounts();
    } catch (err) {
      console.error(err);
      alert("Failed to delete transaction");
    }
  });
});

async function loadAccounts() {
  const container = document.getElementById("ledgerContainer");
  if (!container) return;
  container.innerHTML = "";

  try {
    const res = await fetch("/api/finances/load_accounts");
    const accounts = await res.json();

    for (const account of accounts) {
      const accountRow = document.createElement("div");
      accountRow.classList.add("account-row");

      let total_expenses = await fetch(`/api/finances/account/total_expenses/${account.account_id}`);
      total_expenses = parseFloat(await total_expenses.text());

      let gross_income = await fetch(`/api/finances/account/total_income/${account.account_id}`);
      gross_income = parseFloat(await gross_income.text());

      accountRow.innerHTML = `
        <div class="account-name">
          <p id='account_text'>${account.account_name} — Gross Income: $${gross_income}</p>
          <p id="balance_text">Balance: $${account.balance.toFixed(2)}</p>
          <p id='expenses_text'>Total Expenses: $${total_expenses.toFixed(2)}</p>
        </div>
        <div class="entry-row">
          <div class="incoming">
            <span class="expense_type_txt">Incoming</span>
            <div class="input-group">
              <input type="number" placeholder="0.00">
              <button data-account="${account.account_id}" data-type="incoming">Submit</button>
            </div>
          </div>
          <div class="outgoing">
            <span class="expense_type_txt">Outgoing</span>
            <div class="input-group">
              <input type="number" placeholder="0.00">
              <button data-account="${account.account_id}" data-type="outgoing">Submit</button>
            </div>
          </div>
        </div>

        <div class="transactions">
          <div class="transactions-column incoming-list">
            <h4>Incoming Transactions</h4>
            <ul></ul>
          </div>
          <div class="transactions-column outgoing-list">
            <h4>Outgoing Transactions</h4>
            <ul></ul>
          </div>
        </div>
      `;

      container.appendChild(accountRow);
      loadTransactions(account.account_id, accountRow);
    }
  } catch (err) {
    console.error("Error loading accounts:", err);
  }
}

async function loadTransactions(accountId, accountRow) {
  try {
    const res = await fetch(`/api/finances/load_transactions/${accountId}`);
    const transactions = await res.json();

    const incomingList = accountRow.querySelector(".incoming-list ul");
    const outgoingList = accountRow.querySelector(".outgoing-list ul");
    if (!incomingList || !outgoingList) return;

    incomingList.innerHTML = "";
    outgoingList.innerHTML = "";

    transactions.forEach(txn => {
      const li = document.createElement("li");
      const sign = txn.is_expense ? "- " : "+ ";
      li.textContent = `${sign}$${txn.amount} — ${txn.description} (${txn.date} ${txn.time})`;

      // Delete button
      const delBtn = document.createElement("button");
      delBtn.textContent = "Delete";
      delBtn.className = "transaction-delete-btn";
      delBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        try {
          const res = await fetch("/api/finances/del_transaction", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ transaction_id: txn.transaction_id })
          });
          if (!res.ok) throw await res.json();
          li.remove();
          loadAccounts();
        } catch (err) {
          console.error("Failed to delete transaction:", err);
          alert("Failed to delete transaction");
        }
      });
      li.appendChild(delBtn);

      // View modal
      li.addEventListener("click", async () => {
        const modal = document.getElementById("viewTransactionModal");
        const receiptContainer = document.getElementById("viewReceiptContainer");
        if (!modal || !receiptContainer) return;

        document.getElementById("viewTransactionTitle").textContent = `${sign}$${txn.amount}`;
        document.getElementById("viewTransactionDesc").textContent = txn.description;

        // Clear old receipt
        receiptContainer.innerHTML = "";

        try {
          // Get MIME type from server
          const mimeRes = await fetch(`/api/transactions/get_receipt_mime/${txn.transaction_id}`);
          let mimeType = "application/octet-stream"; // fallback
          if (mimeRes.ok) {
            mimeType = (await mimeRes.text()).trim() || mimeType;
          }

          const receiptRes = await fetch(`/api/finances/get_receipt/${txn.transaction_id}`);
          if (receiptRes.ok) {
            const blob = await receiptRes.blob();

            if (blob.size === 0) {
              receiptContainer.textContent = "No receipt available";
              return;
            }

            // Use server-provided MIME type
            if (mimeType.startsWith("image/")) {
              const img = document.createElement("img");
              img.src = URL.createObjectURL(blob);
              img.style.maxWidth = "100%";
              img.style.display = "block";
              receiptContainer.appendChild(img);
            } else {
              const link = document.createElement("a");
              link.href = URL.createObjectURL(blob);
              link.download = txn.description || "file";
              link.textContent = "Download Receipt";
              link.style.display = "inline-block";
              link.style.marginTop = "10px";
              receiptContainer.appendChild(link);
            }
          }
        } catch (err) {
          console.error("Failed to load receipt:", err);
          receiptContainer.textContent = "Failed to load receipt";
        }

        modal.dataset.txnId = txn.transaction_id;
        modal.style.display = "flex";
      });

      // Append transaction to correct list
      if (txn.is_expense) outgoingList.appendChild(li);
      else incomingList.appendChild(li);
    }); // end of forEach
  } catch (err) {
    console.error(`Error loading transactions for account ${accountId}:`, err);
  }
}
