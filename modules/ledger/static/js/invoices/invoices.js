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
const billingName = document.getElementById("billing-name");
const billingAddress = document.getElementById("billing-address");
const billingEmail = document.getElementById("billing-email");
const billingPhone = document.getElementById("billing-phone");
const invoiceNotes = document.getElementById("invoice-notes");

let items = [];

// ------------------------
// Helpers
// ------------------------
async function apiFetch(url, options = {}) {
  try {
    const res = await fetch(url, options);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json();
  } catch (err) {
    console.error("API error:", err);
    throw err;
  }
}

function groupItems(list) {
  const grouped = {};
  list.forEach(({ name, price }) => {
    if (!grouped[name]) grouped[name] = { name, price: 0, qty: 0 };
    grouped[name].qty++;
    grouped[name].price += price;
  });
  return Object.values(grouped);
}

// ------------------------
// Load Items
// ------------------------
async function loadItems() {
  try {
    const allItems = await apiFetch("/api/ledger/invoices/get-items");
    itemList.innerHTML = "";

    allItems.forEach((item) => {
      const li = document.createElement("li");
      li.dataset.name = item.name;
      li.dataset.price = item.price;

      li.innerHTML = `
        <span class="item-name">${item.name} — $${item.price}</span>
        <button class="delete-item-btn">🗑️</button>
      `;

      // Add item to invoice
      li.addEventListener("click", (e) => {
        if (e.target.closest(".delete-item-btn")) return; // skip delete
        items.push({ name: item.name, price: parseFloat(item.price) });
        updateInvoice();
      });

      // Delete button
      li.querySelector(".delete-item-btn").addEventListener("click", async (e) => {
        e.stopPropagation();
        await apiFetch("/api/ledger/invoices/delete-item", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: item.name }),
        });
        loadItems();
      });

      itemList.appendChild(li);
    });
  } catch (err) {}
}

// ------------------------
// Add Custom Item
// ------------------------
addItemForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = newItemName.value.trim();
  const price = parseFloat(newItemPrice.value);
  if (!name || isNaN(price)) return;

  await apiFetch("/api/ledger/invoices/add-item", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, price }),
  });

  newItemName.value = "";
  newItemPrice.value = "";
  loadItems();
});

// ------------------------
// Update Invoice Preview
// ------------------------
function updateInvoice() {
  invoiceTableBody.innerHTML = "";
  let total = 0;

  groupItems(items).forEach((item, idx) => {
    total += item.price;
    const row = document.createElement("tr");

    row.innerHTML = `
      <td>${item.name}</td>
      <td>${item.qty}</td>
      <td>$${item.price.toFixed(2)}</td>
      <td><button class="remove-item-btn" data-name="${item.name}">✖</button></td>
    `;

    invoiceTableBody.appendChild(row);
  });

  invoiceTotal.textContent = `$${total.toFixed(2)}`;
}

// ------------------------
// Save Invoice
// ------------------------
async function saveInvoice() {
  if (!items.length) return alert("Invoice is empty!");
  const total = items.reduce((sum, i) => sum + i.price, 0);
  const cfid = cfidInput.value ? parseInt(cfidInput.value) : null;

  const details = {
    billing_name: billingName.value.trim(),
    billing_address: billingAddress.value.trim(),
    billing_email_address: billingEmail.value.trim(),
    billing_phone: billingPhone.value.trim(),
    billing_notes: invoiceNotes.value.trim(),
  };

  await apiFetch("/api/ledger/invoices/save-invoice", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items, total, cfid, "details": details }),
  });

  // Reset after save
  items = [];
  cfidInput.value = "";
  billingName.value = "";
  billingAddress.value = "";
  billingEmail.value = "";
  billingPhone.value = "";
  invoiceNotes.value = "";
  updateInvoice();
  loadPastInvoices();
}

// ------------------------
// Load Past Invoices
// ------------------------
async function loadPastInvoices() {
  try {
    const saved = await apiFetch("/api/ledger/invoices/get-invoices", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        searchTerm: searchBox.value,
        StatusFilter: filterStatus.value,
      }),
    });

    pastInvoicesList.innerHTML = "";
    saved.forEach((inv) => {
      const nameDisplay = inv.billing_name ? `Invoice for ${inv.billing_name}` : "Invoice";
      pastInvoicesList.insertAdjacentHTML(
        "beforeend",
        `
        <li class="invoice-card">
          <div class="invoice-header">
            <div class="invoice-date"><strong>${inv.date}</strong></div>
            <div class="invoice-status">
              <span class="status ${inv.paid ? "paid" : "unpaid"}">
                ${inv.paid ? "Paid" : "Unpaid"}
              </span>
            </div>
          </div>
          <div class="invoice-body">
            <div class="invoice-customer">${nameDisplay}</div>
            <div class="invoice-total">Total: $${inv.total}</div>
          </div>
          <div class="invoice-buttons">
            <button data-id="${inv.id}" class="load-btn">Load</button>
            <button data-id="${inv.id}" class="pdf-btn">PDF</button>
            <button data-id="${inv.id}" class="toggle-paid-btn">
              ${inv.paid ? "Mark Unpaid" : "Mark Paid"}
            </button>
          </div>
        </li>
        `
      );
    });
  } catch (err) {}
}

// ------------------------
// Past Invoice Actions
// ------------------------
pastInvoicesList.addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-id]");
  if (!btn) return;
  const id = btn.dataset.id;

  if (btn.classList.contains("load-btn")) {
    const invoice = await apiFetch(`/api/ledger/invoices/get-invoice/${id}`);
    items = [...invoice.items];
    cfidInput.value = invoice.cfid || "";

    // Populate billing details from new top-level fields
    billingName.value = invoice.billing_name || "";
    billingAddress.value = invoice.billing_address || "";
    billingEmail.value = invoice.billing_email_address || "";
    billingPhone.value = invoice.billing_phone || "";
    invoiceNotes.value = invoice.billing_notes || "";

    updateInvoice();
  }

  if (btn.classList.contains("pdf-btn")) {
    const invoice = await apiFetch(`/api/ledger/invoices/get-invoice/${id}`);
    generatePDF(invoice);
  }

  if (btn.classList.contains("toggle-paid-btn")) {
    const invoice = await apiFetch(`/api/ledger/invoices/get-invoice/${id}`);
    await apiFetch(`/api/ledger/invoices/toggle-paid`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paid: !invoice.paid, invoice_id: id }),
    });
    loadPastInvoices();
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
    total: items.reduce((sum, i) => sum + i.price, 0),
    paid: false,
    billing_name: billingName.value.trim(),
    billing_address: billingAddress.value.trim(),
    billing_email_address: billingEmail.value.trim(),
    billing_phone: billingPhone.value.trim(),
    billing_notes: invoiceNotes.value.trim(),
  };

  // Header
  doc.setFontSize(22).setFont("helvetica", "bold");
  doc.text("INVOICE", 14, 20);

  doc.setFontSize(11).setFont("helvetica", "normal");
  doc.text(`Date: ${data.date}`, 14, 30);

  // Billing info
  let y = 40;
  if (data.billing_name) { doc.text(`Bill To: ${data.billing_name}`, 14, y); y += 6; }
  if (data.billing_address) { doc.text(data.billing_address, 14, y); y += 6; }
  if (data.billing_email_address) { doc.text(`Email: ${data.billing_email_address}`, 14, y); y += 6; }
  if (data.billing_phone) { doc.text(`Phone: ${data.billing_phone}`, 14, y); y += 6; }

  // Separator line before table
  y += 4;
  doc.setDrawColor(100).setLineWidth(0.5).line(14, y, 196, y);
  y += 10;

  // Notes at bottom
  if (data.billing_notes) {
    doc.setFontSize(10).setTextColor(80);
    doc.text(`Notes: ${data.billing_notes}`, 14, 275);
  }

  doc.save("invoice.pdf");
}

// ------------------------
// Bindings
// ------------------------
document.getElementById("save-invoice").addEventListener("click", saveInvoice);
document.getElementById("generate-pdf").addEventListener("click", () => generatePDF());
filterStatus.addEventListener("change", loadPastInvoices);
searchBox.addEventListener("input", loadPastInvoices);

invoiceTableBody.addEventListener("click", (e) => {
  if (e.target.classList.contains("remove-item-btn")) {
    const name = e.target.dataset.name;
    items = items.filter((i) => i.name !== name);
    updateInvoice();
  }
});

// Hide/show billing name based on CFID
function toggleBillingNameVisibility() {
  const hasCFID = cfidInput.value && cfidInput.value.trim() !== "";
  billingName.parentElement.style.display = hasCFID ? "none" : "";
  billingName.required = !hasCFID;
}

// Run on CFID input change
cfidInput.addEventListener("input", toggleBillingNameVisibility);

// Initial check
toggleBillingNameVisibility();

// ------------------------
// Initial Load
// ------------------------
loadItems();
loadPastInvoices();
