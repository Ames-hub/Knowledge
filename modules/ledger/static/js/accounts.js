document.addEventListener("DOMContentLoaded", () => {
  loadAccounts();
});

async function loadAccounts() {
  const container = document.getElementById("ledgerContainer");
  container.innerHTML = ""; // clear old rows

  try {
    const res = await fetch("/api/finances/load_accounts");
    const accounts = await res.json();

    for (const account of accounts) {
      // Create account row
      const accountRow = document.createElement("div");
      accountRow.classList.add("account-row");

      accountRow.innerHTML = `
        <div class="account-name">
          ${account.account_name} — Balance: $${account.balance.toFixed(2)}
        </div>
        <div class="entry-row">
          <div class="incoming">
            <span>Incoming</span>
            <div class="input-group">
              <input type="number" placeholder="0.00">
              <button data-account="${account.account_id}" data-type="incoming">Submit</button>
            </div>
          </div>
          <div class="outgoing">
            <span>Outgoing</span>
            <div class="input-group">
              <input type="number" placeholder="0.00">
              <button data-account="${account.account_id}" data-type="outgoing">Submit</button>
            </div>
          </div>
        </div>

        <!-- Transactions -->
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

      // Load transactions for this account
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

    incomingList.innerHTML = "";
    outgoingList.innerHTML = "";

    transactions.forEach(txn => {
      const li = document.createElement("li");
      const sign = txn.is_expense ? "- " : "+ ";
      li.textContent = `${sign}$${txn.amount} — ${txn.description} (${txn.date} ${txn.time})`;

      if (txn.is_expense) {
        outgoingList.appendChild(li);
      } else {
        incomingList.appendChild(li);
      }
    });
  } catch (err) {
    console.error(`Error loading transactions for account ${accountId}:`, err);
  }
}
