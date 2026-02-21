// Accounts.js

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
      
      // Add class based on account type
      if (account.is_double_entry === false) {
        accountRow.classList.add("single-entry");
      }

      let total_expenses = await fetch(`/api/finances/account/total_expenses/${account.account_id}`);
      total_expenses = parseFloat(await total_expenses.text());

      let gross_income = await fetch(`/api/finances/account/total_income/${account.account_id}`);
      gross_income = parseFloat(await gross_income.text());

      // Build HTML based on account type
      if (account.is_double_entry) {
        // Double-entry layout
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
                <input type="number" placeholder="0.00" class="incoming-input">
                <button data-account="${account.account_id}" data-type="incoming" class="incoming-btn">Submit</button>
              </div>
            </div>
            <div class="outgoing">
              <span class="expense_type_txt">Outgoing</span>
              <div class="input-group">
                <input type="number" placeholder="0.00" class="outgoing-input">
                <button data-account="${account.account_id}" data-type="outgoing" class="outgoing-btn">Submit</button>
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
      } else {
        // Single-entry layout - combined
        accountRow.innerHTML = `
          <div class="account-name">
            <p id='account_text'>${account.account_name} — Gross Income: $${gross_income}</p>
            <p id="balance_text">Balance: $${account.balance.toFixed(2)}</p>
            <p id='expenses_text'>Total Expenses: $${total_expenses.toFixed(2)}</p>
          </div>
          <div class="entry-row">
            <div class="combined-entry">
              <span>Amount</span>
              <div class="input-group">
                <input type="number" placeholder="0.00" class="combined-input" id="combined-amount-${account.account_id}">
                <select class="transaction-type-select" id="type-select-${account.account_id}">
                  <option value="incoming">Income</option>
                  <option value="outgoing">Expense</option>
                </select>
                <button data-account="${account.account_id}" class="combined-btn">Submit</button>
              </div>
            </div>
          </div>

          <div class="transactions">
            <div class="transactions-column combined-list">  <!-- Changed: single column -->
              <ul></ul>  <!-- Single list for all transactions -->
            </div>
          </div>
        `;
      }

      container.appendChild(accountRow);
      
      // Attach event listeners based on account type
      if (account.is_double_entry) {
        attachDoubleEntryListeners(accountRow, account.account_id);
      } else {
        attachSingleEntryListeners(accountRow, account.account_id);
      }
      
      loadTransactions(account.account_id, accountRow);
    }
  } catch (err) {
    console.error("Error loading accounts:", err);
  }
}

function attachDoubleEntryListeners(accountRow, accountId) {
  // Incoming submit
  const incomingBtn = accountRow.querySelector('.incoming-btn');
  const incomingInput = accountRow.querySelector('.incoming-input');
  
  incomingBtn?.addEventListener('click', async () => {
    const amount = incomingInput.value;
    if (!amount || amount <= 0) {
      alert('Please enter a valid amount');
      return;
    }
    
    // Trigger transaction modal with incoming type
    openTransactionModal(accountId, 'incoming', amount);
  });

  // Outgoing submit
  const outgoingBtn = accountRow.querySelector('.outgoing-btn');
  const outgoingInput = accountRow.querySelector('.outgoing-input');
  
  outgoingBtn?.addEventListener('click', async () => {
    const amount = outgoingInput.value;
    if (!amount || amount <= 0) {
      alert('Please enter a valid amount');
      return;
    }
    
    // Trigger transaction modal with outgoing type
    openTransactionModal(accountId, 'outgoing', amount);
  });
}

function attachSingleEntryListeners(accountRow, accountId) {
  const submitBtn = accountRow.querySelector('.combined-btn');
  const amountInput = accountRow.querySelector('.combined-input');
  const typeSelect = accountRow.querySelector('.transaction-type-select');
  
  submitBtn?.addEventListener('click', async () => {
    const amount = amountInput.value;
    if (!amount || amount <= 0) {
      alert('Please enter a valid amount');
      return;
    }
    
    const type = typeSelect?.value || 'incoming';
    
    // Trigger transaction modal with selected type
    openTransactionModal(accountId, type, amount);
  });
}

function openTransactionModal(accountId, type, amount) {
  const modal = document.getElementById("transactionModal");
  if (!modal) return;
  
  // Set the money text
  const moneyText = document.getElementById("moneyText");
  if (moneyText) {
    moneyText.textContent = `${type === 'incoming' ? '+' : '-'}$${parseFloat(amount).toFixed(2)}`;
  }
  
  // Store account and amount data on modal
  modal.dataset.accountId = accountId;
  modal.dataset.transactionType = type;
  modal.dataset.amount = amount;
  
  // Show modal
  modal.style.display = "flex";
}

async function loadTransactions(accountId, accountRow) {
  try {
    const res = await fetch(`/api/finances/load_transactions/${accountId}`);
    const transactions = await res.json();

    // Check if this is a single-entry account
    const isSingleEntry = accountRow.classList.contains('single-entry');
    
    if (isSingleEntry) {
      // Single-entry: use combined list
      const combinedList = accountRow.querySelector(".combined-list ul");
      if (!combinedList) return;
      
      combinedList.innerHTML = "";

      transactions.forEach(txn => {
        const li = document.createElement("li");
        const sign = txn.is_expense ? "- " : "+ ";
        li.textContent = `${sign}$${txn.amount} — ${txn.description} (${txn.date} ${txn.time})`;
        
        // Add class for border color
        if (txn.is_expense) {
          li.classList.add('expense-item');
        } else {
          li.classList.add('income-item');
        }

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

        // View modal (same as before)
        li.addEventListener("click", async () => {
          // ... keep existing view modal code ...
        });

        combinedList.appendChild(li);
      });
    } else {
      // Double-entry: use separate lists (existing code)
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
          // ... keep existing view modal code ...
        });

        if (txn.is_expense) {
          outgoingList.appendChild(li);
        } else {
          incomingList.appendChild(li);
        }
      });
    }
  } catch (err) {
    console.error(`Error loading transactions for account ${accountId}:`, err);
  }
}

// Also update your transaction modal preset buttons
document.addEventListener("DOMContentLoaded", () => {
  // Preset buttons for transaction description
  const presetButtons = document.querySelectorAll(".preset-options button");
  const transactionDesc = document.getElementById("transactionDesc");
  
  presetButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      if (transactionDesc) {
        transactionDesc.value = btn.dataset.value || btn.textContent;
      }
    });
  });
  
  // Cancel button for transaction modal
  document.getElementById("cancelBtn")?.addEventListener("click", () => {
    const modal = document.getElementById("transactionModal");
    if (modal) {
      modal.style.display = "none";
      document.getElementById("transactionDesc").value = "";
      document.getElementById("receiptInput").value = "";
    }
  });
});