const itemList = document.getElementById("item-list");
const invoiceTableBody = document.querySelector("#invoice-table tbody");
const invoiceTotal = document.getElementById("invoice-total");
const pastInvoicesList = document.getElementById("past-invoices");
const filterStatus = document.getElementById("filter-status");
const searchBox = document.getElementById("search-invoices");
const addItemForm = document.getElementById("add-item-form");
const newItemName = document.getElementById("new-item-name");
const newItemPrice = document.getElementById("new-item-price");
const cfidInput = document.getElementById("cfid-input");

let items = [];

// ------------------------
// Load Items from API
// ------------------------
async function loadItems() {
  try {
    const res = await fetch("/api/ledger/invoices/get-items");
    const allItems = await res.json();

    itemList.innerHTML = ""; // clear everything first
    allItems.forEach((item) => {
      const li = document.createElement("li");
      li.dataset.name = item.name;
      li.dataset.price = item.price;

      // Item text
      const span = document.createElement("span");
      span.textContent = `${item.name} — $${item.price}`;
      span.classList.add("item-name");
      li.appendChild(span);

      // Delete button
      const delBtn = document.createElement("button");
      delBtn.textContent = "🗑️";
      delBtn.classList.add("delete-item-btn");
      delBtn.onclick = async (e) => {
        e.stopPropagation();

        try {
          await fetch(`/api/ledger/invoices/delete-item`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: item.name }),
          });
          loadItems();
        } catch (err) {
          console.error("Failed to delete item:", err);
        }
      };
      li.appendChild(delBtn);

      // Click to add to invoice (on LI only)
      li.onclick = () => {
        const name = item.name;
        const price = parseFloat(item.price);
        items.push({ name, price });
        updateInvoice();
      };

      itemList.appendChild(li);
    });
  } catch (err) {
    console.error("Failed to load items:", err);
  }
};

// ------------------------
// Add Custom Item
// ------------------------
addItemForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = newItemName.value.trim();
  const price = parseFloat(newItemPrice.value);
  if (!name || isNaN(price)) return;

  try {
    await fetch("/api/ledger/invoices/add-item", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, price }),
    });

    newItemName.value = "";
    newItemPrice.value = "";
    loadItems();
  } catch (err) {
    console.error("Failed to add item:", err);
  }
});

// ------------------------
// Update Invoice Preview
// ------------------------
function updateInvoice() {
  invoiceTableBody.innerHTML = "";
  let total = 0;

  // Group items by name
  const grouped = {};
  items.forEach(item => {
    if (grouped[item.name]) {
      grouped[item.name].qty += 1;
      grouped[item.name].price += item.price;
    } else {
      grouped[item.name] = { ...item, qty: 1 };
    }
  });

  // Render grouped items
  Object.values(grouped).forEach((item, index) => {
    total += item.price;
    const row = document.createElement("tr");

    const nameCell = document.createElement("td");
    nameCell.textContent = item.name;

    const qtyCell = document.createElement("td");
    qtyCell.textContent = item.qty;

    const priceCell = document.createElement("td");
    priceCell.textContent = `$${item.price.toFixed(2)}`;

    const removeCell = document.createElement("td");
    const removeBtn = document.createElement("button");
    removeBtn.textContent = "✖";
    removeBtn.onclick = () => {
      // Remove all of that item from items array
      items = items.filter(i => i.name !== item.name);
      updateInvoice();
    };
    removeCell.appendChild(removeBtn);

    row.appendChild(nameCell);
    row.appendChild(qtyCell);
    row.appendChild(priceCell);
    row.appendChild(removeCell);

    invoiceTableBody.appendChild(row);
  });

  invoiceTotal.textContent = `$${total.toFixed(2)}`;
}

// ------------------------
// Save Invoice to API
// ------------------------
async function saveInvoice() {
  if (items.length === 0) return alert("Invoice is empty!");
  const total = items.reduce((acc, i) => acc + i.price, 0);
  const cfid = cfidInput.value ? parseInt(cfidInput.value) : null;

  try {
    await fetch("/api/ledger/invoices/save-invoice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items, total, cfid }),
    });

    items = [];
    cfidInput.value = ""; // reset
    updateInvoice();
    loadPastInvoices();
  } catch (err) {
    console.error("Failed to save invoice:", err);
  }
}

// ------------------------
// Load Past Invoices
// ------------------------
async function loadPastInvoices() {
  const statusFilter = filterStatus.value;
  const searchTerm = searchBox.value;

  try {
    const res = await fetch(
      `/api/ledger/invoices/get-invoices`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ searchTerm: searchTerm, StatusFilter: statusFilter })
      }
    );
    const saved = await res.json();

    pastInvoicesList.innerHTML = "";
    saved.forEach((inv) => {
      const li = document.createElement("li");
      li.classList.add("invoice-card");

      const status = inv.paid
        ? "<span class='status paid'>Paid</span>"
        : "<span class='status unpaid'>Unpaid</span>";

      li.innerHTML = `
        <div class="invoice-header">
          <div class="invoice-date"><strong>${inv.date}</strong></div>
          <div class="invoice-status">${status}</div>
        </div>
        <div class="invoice-body">
          <div class="invoice-total">Total: $${inv.total}</div>
        </div>
        <div class="invoice-buttons">
          <button data-id="${inv.id}" class="load-btn">Load</button>
          <button data-id="${inv.id}" class="pdf-btn">PDF</button>
          <button data-id="${inv.id}" class="toggle-paid-btn">
            ${inv.paid ? "Mark Unpaid" : "Mark Paid"}
          </button>
        </div>
      `;
      pastInvoicesList.appendChild(li);
    });
  } catch (err) {
    console.error("Failed to load past invoices:", err);
  }
}

// ------------------------
// Past Invoice Button Actions
// ------------------------
pastInvoicesList.addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-id]");
  if (!btn) return;
  const id = btn.dataset.id;

  // Load invoice
  if (btn.classList.contains("load-btn")) {
    try {
      const res = await fetch(`/api/ledger/invoices/get-invoice/${id}`);
      const invoice = await res.json();
      items = [...invoice.items];
      cfidInput.value = invoice.cfid
      updateInvoice();
    } catch (err) {
      console.error("Failed to load invoice:", err);
    }
  }

  // Generate PDF (frontend)
  if (btn.classList.contains("pdf-btn")) {
    try {
      const res = await fetch(`/api/ledger/invoices/get-invoice/${id}`);
      const invoice = await res.json();
      generatePDF(invoice);
    } catch (err) {
      console.error("Failed to generate PDF:", err);
    }
  }

  // Toggle Paid Status
  if (btn.classList.contains("toggle-paid-btn")) {
    try {
      const res = await fetch(`/api/ledger/invoices/get-invoice/${id}`);
      const invoice = await res.json();

      await fetch(`/api/ledger/invoices/toggle-paid`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ paid: !invoice.paid, invoice_id: id }),
      });

      loadPastInvoices();
    } catch (err) {
      console.error("Failed to toggle paid status:", err);
    }
  }
});

// ------------------------
// Generate PDF
// ------------------------
function generatePDF(invoice = null) {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF();

  const data = invoice || {
    date: new Date().toLocaleString(),
    items,
    total: items.reduce((acc, i) => acc + i.price, 0),
    paid: false,
  };

  // Group items by name
  const grouped = {};
  data.items.forEach(item => {
    if (grouped[item.name]) {
      grouped[item.name].qty += 1;
      grouped[item.name].price += item.price;
    } else {
      grouped[item.name] = { ...item, qty: 1 };
    }
  });

  const groupedItems = Object.values(grouped);

  // Header
  doc.setFontSize(22);
  doc.setFont("helvetica", "bold");
  doc.text("INVOICE", 14, 20);

  doc.setFontSize(11);
  doc.setFont("helvetica", "normal");
  doc.text(`Date: ${data.date}`, 14, 30);

  // Fancy separator
  doc.setDrawColor(100);
  doc.setLineWidth(0.5);
  doc.line(14, 42, 196, 42);

  // Column headers
  doc.setFont("helvetica", "bold");
  doc.text("#", 14, 50);
  doc.text("Item", 25, 50);
  doc.text("Qty", 130, 50, { align: "right" });
  doc.text("Price", 160, 50, { align: "right" });

  doc.setFont("helvetica", "normal");
  let y = 58;
  groupedItems.forEach((item, i) => {
    doc.text(`${i + 1}`, 14, y);
    doc.text(`${item.name}`, 25, y);
    doc.text(`${item.qty}`, 130, y, { align: "right" });
    doc.text(`$${item.price.toFixed(2)}`, 160, y, { align: "right" });
    y += 8;
  });

  // Total
  y += 4;
  doc.setFont("helvetica", "bold");
  doc.text(`Total: $${data.total.toFixed(2)}`, 160, y, { align: "right" });

  // Paid stamp
  if (data.paid) {
    doc.setFontSize(40);
    doc.setTextColor(0, 128, 0);
    doc.text("PAID", 105, y / 2 + 50, { angle: 45, align: "center" });
    doc.setTextColor(0); // reset color
  }

  // Footer
  doc.setFontSize(9);
  doc.setTextColor(150);
  doc.text("Thank you for your business!", 14, 285);

  doc.save("invoice.pdf");
}

// ------------------------
// Button Bindings
// ------------------------
document.getElementById("save-invoice").addEventListener("click", saveInvoice);
document.getElementById("generate-pdf").addEventListener("click", () => generatePDF());
filterStatus.addEventListener("change", loadPastInvoices);
searchBox.addEventListener("input", loadPastInvoices);

// ------------------------
// Initial Load
// ------------------------
loadItems();
loadPastInvoices();
