// ====== invoices.js ======
class InvoiceManager {
  constructor() {
    this.items = [];
    this.currentInvoice = [];
    this.pastInvoices = [];
    
    this.initElements();
    this.bindEvents();
    this.loadData();
  }
  
  initElements() {
    // Core elements - FIXED: Changed IDs to match HTML
    this.itemList = document.getElementById('item-list');
    this.invoiceTableBody = document.getElementById('invoice-table-body'); // FIXED
    this.invoiceTotal = document.getElementById('invoice-total');
    this.historyList = document.getElementById('history-list');
    this.itemCount = document.getElementById('item-count');
    
    // Forms
    this.addItemForm = document.getElementById('add-item-form');
    this.detailsForm = document.getElementById('details-form');
    
    // Inputs
    this.cfidInput = document.getElementById('cfid-input');
    this.searchInput = document.getElementById('search-invoices');
    this.statusFilter = document.getElementById('filter-status');
    
    // Item form inputs - FIXED: Get elements directly
    this.newItemName = document.getElementById('new-item-name');
    this.newItemPrice = document.getElementById('new-item-price');
    
    // Billing details
    this.billingName = document.getElementById('billing-name');
    this.billingAddress = document.getElementById('billing-address');
    this.billingEmail = document.getElementById('billing-email');
    this.billingPhone = document.getElementById('billing-phone');
    this.billingNotes = document.getElementById('invoice-notes');
    
    // Buttons
    this.saveBtn = document.getElementById('save-invoice');
    this.pdfBtn = document.getElementById('generate-pdf');
    
    // Validate all required elements exist
    this.validateElements();
  }
  
  validateElements() {
    const requiredElements = {
      'itemList': this.itemList,
      'invoiceTableBody': this.invoiceTableBody,
      'invoiceTotal': this.invoiceTotal,
      'historyList': this.historyList,
      'addItemForm': this.addItemForm,
      'saveBtn': this.saveBtn,
      'pdfBtn': this.pdfBtn
    };
    
    for (const [name, element] of Object.entries(requiredElements)) {
      if (!element) {
        console.error(`Required element not found: ${name}`);
        throw new Error(`Missing element: ${name}`);
      }
    }
  }
  
  bindEvents() {
    // Item management
    this.addItemForm.addEventListener('submit', (e) => this.addNewItem(e));
    
    // Invoice actions
    this.saveBtn.addEventListener('click', () => this.saveInvoice());
    this.pdfBtn.addEventListener('click', () => this.generatePDF(this.invoiceId));
    
    // Filters
    this.searchInput?.addEventListener('input', () => this.filterInvoices());
    this.statusFilter?.addEventListener('change', () => this.filterInvoices());
    
    // CFID handling - only when typing CFID, not when loading
    this.cfidInput?.addEventListener('input', () => this.setBillingNameFromCFID());
  }
  
  async loadData() {
    try {
      await Promise.all([
        this.loadItems(),
        this.loadPastInvoices()
      ]);
    } catch (error) {
      console.error('Failed to load data:', error);
      this.showToast('Failed to load data', 'error');
    }
  }
  
  async apiRequest(endpoint, options = {}) {
    try {
      const response = await fetch(`/api/ledger/invoices${endpoint}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      this.showToast(error.message, 'error');
      throw error;
    }
  }
  
  async loadItems() {
    try {
      this.showLoading(this.itemList, 'Loading items...');
      const items = await this.apiRequest('/get-items');
      this.items = items;
      this.renderItems(items);
      this.updateItemCount();
    } catch (error) {
      console.error('Failed to load items:', error);
      this.showEmptyState(this.itemList, 'Failed to load items');
    }
  }
  
  renderItems(items) {
    if (!items || items.length === 0) {
      this.showEmptyState(this.itemList, 'No items available');
      this.updateItemCount();
      return;
    }
    
    this.itemList.innerHTML = items.map(item => `
      <li class="item-card" data-name="${item.name}">
        <div class="item-info">
          <h4>${item.name}</h4>
          <span class="item-price">$${parseFloat(item.price).toFixed(2)}</span>
        </div>
        <button class="delete-item" data-name="${item.name}" title="Delete item">
          <i class="fas fa-trash"></i>
        </button>
      </li>
    `).join('');
    
    // Add event listeners
    this.itemList.querySelectorAll('.item-card').forEach(card => {
      const itemName = card.dataset.name;
      const item = this.items.find(i => i.name === itemName);
      
      card.addEventListener('click', (e) => {
        if (e.target.closest('.delete-item')) {
          e.stopPropagation();
          this.deleteItem(itemName);
          return;
        }
        if (item) {
          this.addToInvoice(item);
        }
      });
    });
    
    this.updateItemCount();
  }
  
  updateItemCount() {
    if (this.itemCount) {
      const count = this.items?.length || 0;
      this.itemCount.textContent = `${count} item${count !== 1 ? 's' : ''}`;
    }
  }
  
  async addNewItem(e) {
    e.preventDefault();
    
    const name = this.newItemName.value.trim();
    const price = parseFloat(this.newItemPrice.value);
    
    if (!name || isNaN(price) || price <= 0) {
      this.showToast('Please enter valid item details', 'warning');
      return;
    }
    
    try {
      this.saveBtn.disabled = true;
      this.pdfBtn.disabled = true;
      
      await this.apiRequest('/add-item', {
        method: 'POST',
        body: JSON.stringify({ name, price })
      });
      
      this.addItemForm.reset();
      await this.loadItems();
      this.showToast('Item added successfully', 'success');
    } catch (error) {
      console.error('Failed to add item:', error);
      this.showToast('Failed to add item', 'error');
    } finally {
      this.saveBtn.disabled = false;
      this.pdfBtn.disabled = false;
    }
  }
  
  async deleteItem(name) {
    if (!confirm('Delete this item permanently?')) return;
    
    try {
      await this.apiRequest('/delete-item', {
        method: 'POST',
        body: JSON.stringify({ name })
      });
      
      await this.loadItems();
      this.showToast('Item deleted', 'success');
    } catch (error) {
      console.error('Failed to delete item:', error);
      this.showToast('Failed to delete item', 'error');
    }
  }
  
  addToInvoice(item) {
    this.currentInvoice.push({
      ...item,
      id: Date.now() + Math.random(),
      timestamp: new Date().toISOString()
    });
    this.updateInvoicePreview();
    this.showToast(`${item.name} added to invoice`, 'success');
  }
  
  updateInvoicePreview() {
    const grouped = this.groupItems(this.currentInvoice);
    
    if (grouped.length === 0) {
      this.invoiceTableBody.innerHTML = `
        <tr class="empty-state-row">
          <td colspan="4" style="text-align: center; padding: 40px; color: var(--text-secondary);">
            <i class="fas fa-receipt" style="font-size: 2rem; opacity: 0.3; margin-bottom: 10px; display: block;"></i>
            <p>Add items from the catalog to build your invoice</p>
          </td>
        </tr>
      `;
    } else {
      this.invoiceTableBody.innerHTML = grouped.map(item => `
        <tr>
          <td><strong>${item.name}</strong></td>
          <td>${item.quantity}</td>
          <td>$${item.total.toFixed(2)}</td>
          <td>
            <button class="btn btn-small btn-danger remove-item" data-name="${item.name}">
              <i class="fas fa-times"></i> Remove
            </button>
          </td>
        </tr>
      `).join('');
    }
    
    const total = this.currentInvoice.reduce((sum, item) => sum + parseFloat(item.price), 0);
    this.invoiceTotal.textContent = `$${total.toFixed(2)}`;
    
    // Add remove event listeners
    this.invoiceTableBody.querySelectorAll('.remove-item').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.removeFromInvoice(btn.dataset.name);
      });
    });
  }
  
  removeFromInvoice(itemName) {
    this.currentInvoice = this.currentInvoice.filter(item => item.name !== itemName);
    this.updateInvoicePreview();
    this.showToast('Item removed from invoice', 'info');
  }
  
  groupItems(items) {
    const groups = {};
    
    items.forEach(item => {
      if (!groups[item.name]) {
        groups[item.name] = {
          name: item.name,
          quantity: 0,
          total: 0
        };
      }
      groups[item.name].quantity++;
      groups[item.name].total += parseFloat(item.price);
    });
    
    return Object.values(groups);
  }
  
  async saveInvoice() {
    if (!this.currentInvoice.length) {
      this.showToast('Add items to the invoice first', 'warning');
      return;
    }
    
    // If CFID is provided, billing name is optional
    const hasCFID = this.cfidInput.value.trim() !== '';
    if (!hasCFID && !this.billingName.value.trim()) {
      this.showToast('Billing name is required when CFID is not provided', 'warning');
      this.billingName.focus();
      return;
    }
    
    const total = this.currentInvoice.reduce((sum, item) => sum + parseFloat(item.price), 0);
    const cfid = this.cfidInput.value ? parseInt(this.cfidInput.value) : null;
    
    const details = {
      billing_name: this.billingName.value.trim(),
      billing_address: this.billingAddress.value.trim(),
      billing_email_address: this.billingEmail.value.trim(),
      billing_phone: this.billingPhone.value.trim(),
      billing_notes: this.billingNotes.value.trim()
    };
    
    try {
      this.saveBtn.disabled = true;
      this.saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
      
      await this.apiRequest('/save-invoice', {
        method: 'POST',
        body: JSON.stringify({
          items: this.currentInvoice,
          total,
          cfid,
          details
        })
      });
      
      // Reset form
      this.currentInvoice = [];
      this.cfidInput.value = '';
      this.detailsForm.reset();
      this.updateInvoicePreview();
      
      await this.loadPastInvoices();
      this.showToast('Invoice saved successfully!', 'success');
    } catch (error) {
      console.error('Failed to save invoice:', error);
      this.showToast('Failed to save invoice', 'error');
    } finally {
      this.saveBtn.disabled = false;
      this.saveBtn.innerHTML = '<i class="fas fa-save"></i> Save Invoice';
    }
  }
  
  async loadPastInvoices() {
    try {
      this.showLoading(this.historyList, 'Loading invoices...');
      const invoices = await this.apiRequest('/get-invoices', {
        method: 'POST',
        body: JSON.stringify({
          searchTerm: this.searchInput?.value || '',
          StatusFilter: this.statusFilter?.value || 'all'
        })
      });
      
      this.pastInvoices = invoices;
      this.renderPastInvoices(invoices);
    } catch (error) {
      console.error('Failed to load invoices:', error);
      this.showEmptyState(this.historyList, 'Failed to load invoices');
    }
  }
  
  renderPastInvoices(invoices) {
    if (!invoices || invoices.length === 0) {
      this.showEmptyState(this.historyList, 'No invoices found');
      return;
    }
    
    this.historyList.innerHTML = invoices.map(inv => {
      // Generate display name: use billing_name if available, otherwise show CFID or "Invoice"
      let displayName = 'Invoice';
      if (inv.billing_name && inv.billing_name.trim() !== '') {
        displayName = inv.billing_name;
      } else if (inv.cfid) {
        displayName = `CFID: ${inv.cfid}`;
      }
      
      return `
      <div class="history-card">
        <div class="history-info">
          <h4>${displayName}</h4>
          <div class="history-meta">
            <span><i class="far fa-calendar"></i> ${inv.date}</span>
            <span><i class="fas fa-dollar-sign"></i> ${parseFloat(inv.total).toFixed(2)}</span>
            <span class="status-badge status-${inv.paid ? 'paid' : 'unpaid'}">
              <i class="fas fa-${inv.paid ? 'check-circle' : 'clock'}"></i>
              ${inv.paid ? 'Paid' : 'Unpaid'}
            </span>
            ${inv.cfid ? `<span><i class="fas fa-id-card"></i> CFID: ${inv.cfid}</span>` : ''}
          </div>
        </div>
        <div class="history-actions">
          <button class="btn btn-small btn-danger del-invoice" data-id="${inv.id}" title="Delete invoice">
            <i class="fas fa-trash"></i>
          </button>
          <button class="btn btn-small btn-secondary load-invoice" data-id="${inv.id}" title="Load invoice">
            <i class="fas fa-upload"></i>
          </button>
          <button class="btn btn-small btn-primary pdf-invoice" data-id="${inv.id}" title="Download PDF">
            <i class="fas fa-file-pdf"></i>
          </button>
          <button class="btn btn-small ${inv.paid ? 'btn-secondary' : 'btn-success'} toggle-paid" data-id="${inv.id}" title="Toggle payment status">
            <i class="fas fa-${inv.paid ? 'undo' : 'check'}"></i>
          </button>
        </div>
      </div>
    `}).join('');
    
    // Add event listeners
    this.addInvoiceEventListeners();
  }
  
  addInvoiceEventListeners() {
    // Delete invoice
    this.historyList.querySelectorAll('.del-invoice').forEach(btn => {
      btn.addEventListener('click', () => this.deleteInvoice(btn.dataset.id));
    });
    
    // Load invoice
    this.historyList.querySelectorAll('.load-invoice').forEach(btn => {
      btn.addEventListener('click', () => this.loadInvoice(btn.dataset.id));
    });
    
    // Generate PDF
    this.historyList.querySelectorAll('.pdf-invoice').forEach(btn => {
      btn.addEventListener('click', () => this.generatePDF(btn.dataset.id));
    });
    
    // Toggle paid status
    this.historyList.querySelectorAll('.toggle-paid').forEach(btn => {
      btn.addEventListener('click', () => this.togglePaidStatus(btn.dataset.id));
    });
  }
  
  async deleteInvoice(id) {
    if (!confirm('Are you sure you want to delete this invoice? This action cannot be undone.')) {
      return;
    }
    
    try {
      // Call the delete endpoint
      await this.apiRequest(`/delete-invoice`, {
        method: 'POST',
        body: JSON.stringify({ invoice_id: id })
      });
      
      // Remove from local array
      this.pastInvoices = this.pastInvoices.filter(inv => inv.id !== id);
      
      // Reload the invoice list
      await this.loadPastInvoices();
      
      this.showToast('Invoice deleted successfully', 'success');
    } catch (error) {
      console.error('Failed to delete invoice:', error);
      this.showToast('Failed to delete invoice', 'error');
    }
  }
  
  async loadInvoice(id) {
    try {
      const invoice = await this.apiRequest(`/get-invoice/${id}`);
      
      // Clear current invoice first
      this.currentInvoice = [];
      
      // Load items (ensure we have proper item objects with name and price)
      if (invoice.items && Array.isArray(invoice.items)) {
        this.currentInvoice = invoice.items.map(item => ({
          name: item.name,
          price: parseFloat(item.price),
          id: Date.now() + Math.random(),
          timestamp: new Date().toISOString()
        }));
      }
      
      this.updateInvoicePreview();
      
      // Load details - IMPORTANT: DO NOT fetch from CFID API when loading
      // Just populate the saved values from the invoice
      if (this.cfidInput) this.cfidInput.value = invoice.cfid || '';
      if (this.billingName) this.billingName.value = invoice.billing_name || '';
      if (this.billingAddress) this.billingAddress.value = invoice.billing_address || '';
      if (this.billingEmail) this.billingEmail.value = invoice.billing_email_address || '';
      if (this.billingPhone) this.billingPhone.value = invoice.billing_phone || '';
      if (this.billingNotes) this.billingNotes.value = invoice.billing_notes || '';
      
      // If CFID exists but billing name is empty, optionally fetch it?
      // Actually NO - we should show what was saved, not refetch
      
      this.showToast('Invoice loaded successfully', 'success');
    } catch (error) {
      console.error('Failed to load invoice:', error);
      this.showToast('Failed to load invoice', 'error');
    }
  }
  
  async togglePaidStatus(id) {
    try {
      const invoice = await this.apiRequest(`/get-invoice/${id}`);
      const newStatus = !invoice.paid;
      
      await this.apiRequest('/toggle-paid', {
        method: 'POST',
        body: JSON.stringify({
          paid: newStatus,
          invoice_id: id
        })
      });
      
      await this.loadPastInvoices();
      this.showToast(`Invoice marked as ${newStatus ? 'paid' : 'unpaid'}`, 'success');
    } catch (error) {
      console.error('Failed to update status:', error);
      this.showToast('Failed to update status', 'error');
    }
  }
  
  async generatePDF(invoiceId = null) {
    try {
      this.pdfBtn.disabled = true;
      this.pdfBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
      
      let invoiceData;
      
      if (invoiceId) {
        invoiceData = await this.apiRequest(`/get-invoice/${invoiceId}`);
      } else {
        if (!this.currentInvoice.length) {
          this.showToast('Add items to the invoice first', 'warning');
          return;
        }
        
        invoiceData = {
          date: new Date().toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
          }),
          items: this.currentInvoice,
          total: this.currentInvoice.reduce((sum, item) => sum + parseFloat(item.price), 0),
          billing_name: this.billingName.value,
          billing_address: this.billingAddress.value,
          billing_email_address: this.billingEmail.value,
          billing_phone: this.billingPhone.value,
          billing_notes: this.billingNotes.value
        };
      }
      
      const { jsPDF } = window.jspdf;
      const doc = new jsPDF();
      
      // PDF Header
      doc.setFontSize(22);
      doc.setFont('helvetica', 'bold');
      doc.text('INVOICE', 20, 20);
      
      doc.setFontSize(11);
      doc.setFont('helvetica', 'normal');
      doc.text(`Date: ${invoiceData.date}`, 20, 30);
      doc.text(`Invoice #: INV-${invoiceId}`, 20, 35);
      
      // Billing Information
      let y = 45;
      if (invoiceData.billing_name) {
        doc.setFont('helvetica', 'bold');
        doc.text('Bill To:', 20, y);
        doc.setFont('helvetica', 'normal');
        doc.text(invoiceData.billing_name, 40, y);
        y += 8;
      }
      
      if (invoiceData.billing_address) {
        const addressLines = invoiceData.billing_address.split('\n');
        addressLines.forEach(line => {
          doc.text(line, 40, y);
          y += 5;
        });
        y += 3;
      }
      
      if (invoiceData.billing_email_address) {
        doc.text(`Email: ${invoiceData.billing_email_address}`, 20, y);
        y += 6;
      }
      
      if (invoiceData.billing_phone) {
        doc.text(`Phone: ${invoiceData.billing_phone}`, 20, y);
        y += 10;
      }
      
      // Table Header
      y += 10;
      doc.setDrawColor(200);
      doc.setLineWidth(0.5);
      doc.line(20, y, 190, y);
      y += 8;
      
      doc.setFont('helvetica', 'bold');
      doc.text('Item', 20, y);
      doc.text('Qty', 120, y);
      doc.text('Price', 150, y);
      doc.text('Total', 170, y);
      
      // Table Items
      y += 8;
      doc.setFont('helvetica', 'normal');
      
      const groupedItems = this.groupItems(invoiceData.items || []);
      groupedItems.forEach(item => {
        doc.text(item.name, 20, y);
        doc.text(item.quantity.toString(), 120, y);
        doc.text(`$${item.total.toFixed(2)}`, 170, y);
        y += 8;
      });
      
      // Total
      y += 10;
      doc.setDrawColor(100);
      doc.line(20, y, 190, y);
      y += 8;
      
      doc.setFont('helvetica', 'bold');
      doc.text('TOTAL:', 140, y);
      doc.text(`$${invoiceData.total.toFixed(2)}`, 170, y);
      
      // Notes
      if (invoiceData.billing_notes) {
        y += 15;
        doc.setFontSize(10);
        doc.setFont('helvetica', 'italic');
        doc.text('Notes:', 20, y);
        doc.text(invoiceData.billing_notes, 20, y + 6);
      }
      
      // Save PDF
      const fileName = invoiceId ? `invoice-${invoiceId}.pdf` : `invoice-${Date.now()}.pdf`;
      doc.save(fileName);
      this.showToast('PDF generated successfully', 'success');
      
    } catch (error) {
      console.error('Failed to generate PDF:', error);
      this.showToast('Failed to generate PDF', 'error');
    } finally {
      this.pdfBtn.disabled = false;
      this.pdfBtn.innerHTML = '<i class="fas fa-file-pdf"></i> Generate PDF';
    }
  }
  
  filterInvoices() {
    this.loadPastInvoices();
  }
  
  setBillingNameFromCFID() {
    if (!this.cfidInput || !this.billingName) return;
    
    const cfid = this.cfidInput.value.trim();
    
    if (!cfid) {
      // If CFID is cleared, show billing name field and make it required
      this.billingName.parentElement.style.display = 'block';
      this.billingName.required = true;
      return;
    }
    
    // First fetch the name
    fetch(`/api/files/${cfid}/name`)
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.text();
      })
      .then(data => {
        const profileName = data;
        
        if (profileName && profileName.trim() !== '') {
          this.billingName.value = profileName;
          // Hide billing name field since we got it from CFID
          this.billingName.parentElement.style.display = 'none';
          this.billingName.required = false;
          
          // Now fetch address and email in parallel
          return Promise.all([
            fetch(`/api/files/${cfid}/address`),
            fetch(`/api/files/${cfid}/email`),
            fetch(`/api/files/${cfid}/phone`)
          ]);
        } else {
          console.error('No name found in API response');
          this.billingName.value = "";
          this.billingName.parentElement.style.display = 'block';
          this.billingName.required = true;
          throw new Error('No name found');
        }
      })
      .then(responses => {
        // Handle all responses
        return Promise.all([
          responses[0].text(),
          responses[1].text(),
          responses[2].text()
        ]);
      })
      .then(dataArray => {
        const profileAddr = dataArray[0];
        const profileEmail = dataArray[1];
        const profilePhone = dataArray[2];
        
        if (profileAddr && profileAddr.trim() !== '') {
          this.billingAddress.value = profileAddr;
        }
        
        if (profileEmail && profileEmail.trim() !== '') {
          this.billingEmail.value = profileEmail;
        }
        
        if (profilePhone && profilePhone.trim() !== '') {
          this.billingPhone.value = profilePhone;
        }
      })
      .catch(error => {
        console.error('Error fetching CFID profile details:', error);
        // On error, show the billing name field and make it required
        this.billingName.parentElement.style.display = 'block';
        this.billingName.required = true;
        this.billingName.value = "";
        this.billingAddress.value = "";
        this.billingEmail.value = "";
        this.billingPhone.value = "";
      });
  }
  
  showEmptyState(container, message) {
    if (!container) return;
    
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📋</div>
        <p>${message}</p>
      </div>
    `;
  }
  
  showLoading(container, message = 'Loading...') {
    if (!container) return;
    
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">
          <i class="fas fa-spinner fa-spin"></i>
        </div>
        <p>${message}</p>
      </div>
    `;
  }
  
  showToast(message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    // Add to page
    document.body.appendChild(toast);
    
    // Remove after delay
    setTimeout(() => {
      if (toast.parentNode) {
        toast.remove();
      }
    }, 3000);
  }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  try {
    new InvoiceManager();
  } catch (error) {
    console.error('Failed to initialize InvoiceManager:', error);
    // Show a user-friendly error message
    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = `
      position: fixed;
      top: 20px;
      left: 50%;
      transform: translateX(-50%);
      background: #ef4444;
      color: white;
      padding: 16px;
      border-radius: 8px;
      z-index: 9999;
      max-width: 90%;
      text-align: center;
    `;
    errorDiv.textContent = 'Failed to load invoice system. Please refresh the page.';
    document.body.appendChild(errorDiv);
  }
});