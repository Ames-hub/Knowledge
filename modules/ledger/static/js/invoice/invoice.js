(function() {
    // ===== INVOICE MANAGER - SPECIFIC INVOICE WITH PAYMENT TRACKING =====
    // Get invoice ID from URL or template context
    const urlParts = window.location.pathname.split('/');
    const INVOICE_ID = parseInt(urlParts[urlParts.length - 1]) || 101; // Fallback to 101 if not found
    
    // Data
    let catalogItems = []; // Will be loaded from API
    let invoiceItems = []; // Will be loaded from API for this invoice
    let payments = []; // Payments for this invoice
    
    // DOM elements
    const itemList = document.getElementById('item-list');
    const invoiceItemsBody = document.getElementById('invoice-items-body');
    const subtotalSpan = document.getElementById('subtotal-amount');
    const subtotalRef = document.getElementById('subtotal-ref');
    const paidTotalSpan = document.getElementById('paid-total');
    const balanceDueSpan = document.getElementById('balance-due');
    const paymentList = document.getElementById('payment-list');
    const paymentCount = document.getElementById('payment-count');
    
    // Forms
    const addItemForm = document.getElementById('add-item-form');
    const newItemName = document.getElementById('new-item-name');
    const newItemPrice = document.getElementById('new-item-price');
    
    // Payment inputs
    const paymentAmount = document.getElementById('payment-amount');
    const paymentMethod = document.getElementById('payment-method');
    const paymentStatus = document.getElementById('payment-status');
    const recordBtn = document.getElementById('record-payment');
    
    // Buttons
    const saveBtn = document.getElementById('save-invoice');
    const pdfBtn = document.getElementById('generate-pdf');
    
    // Details inputs
    const cfidInput = document.getElementById('cfid-input');
    const billingName = document.getElementById('billing-name');
    const billingAddress = document.getElementById('billing-address');
    const billingEmail = document.getElementById('billing-email');
    const billingPhone = document.getElementById('billing-phone');
    const billingNotes = document.getElementById('invoice-notes');
    
    // Invoice header
    document.querySelector('.card-header .badge').innerHTML = `Invoice #INV-${INVOICE_ID}`;
    document.querySelector('.payments-header h2').innerHTML = `<i class="fas fa-credit-card"></i> Payments on Invoice #${INVOICE_ID}`;
    
    // ===== API CALLS =====
    async function loadInvoiceData() {
        try {
            const response = await fetch(`/api/ledger/invoices/get-invoice/${INVOICE_ID}`);
            if (response.ok) {
                const invoice = await response.json();
                
                // Populate invoice items
                if (invoice.items && invoice.items.length > 0) {
                    invoiceItems = invoice.items.map(item => ({
                        name: item.name,
                        price: item.price,
                        quantity: 1 // Default quantity, you might want to store this in DB
                    }));
                }
                
                // Populate details form
                cfidInput.value = invoice.cfid || '';
                billingName.value = invoice.billing_name || '';
                billingAddress.value = invoice.billing_address || '';
                billingEmail.value = invoice.billing_email_address || '';
                billingPhone.value = invoice.billing_phone || '';
                billingNotes.value = invoice.billing_notes || '';
            }
        } catch (error) {
            console.error('Error loading invoice:', error);
        }
    }
    
    async function loadCatalogItems() {
        try {
            const response = await fetch('/api/ledger/invoices/get-items');
            if (response.ok) {
                catalogItems = await response.json();
                renderCatalog();
            }
        } catch (error) {
            console.error('Error loading catalog:', error);
        }
    }
    
    async function loadPayments() {
        try {
            const response = await fetch(`/api/ledger/invoices/${INVOICE_ID}/payments`);
            if (response.ok) {
                payments = await response.json();
            } else {
                payments = [];
                showToast('Error loading payments', 'error');
            }
        } catch (error) {
            console.error('Error loading payments:', error);
            payments = [];
            showToast('Failed to load payments', 'error');
        }
        renderPayments();
    }
    
    async function recordPayment(amount, method, status) {
        try {
            const response = await fetch('/api/ledger/invoices/record-payment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    invoice_id: INVOICE_ID,
                    amount: amount,
                    payment_method: method,
                    payment_status: status,
                    notes: ''
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                await loadPayments(); // Reload all payments to get the updated list
                renderInvoiceItems();
                showToast('Payment recorded successfully', 'success');
                paymentAmount.value = '';
            } else {
                showToast('Error recording payment', 'error');
            }
        } catch (error) {
            console.error('Error recording payment:', error);
            showToast('Failed to record payment', 'error');
        }
    }
    
    // ===== HELPER FUNCTIONS =====
    function calculateTotals() {
        const subtotal = invoiceItems.reduce((sum, item) => sum + (item.price * (item.quantity || 1)), 0);
        const paid = payments
            .filter(p => p.invoiceId === INVOICE_ID && p.status === 'completed')
            .reduce((sum, p) => sum + p.amount, 0);
        const balance = subtotal - paid;
        return { subtotal, paid, balance };
    }
    
    function updateAll() {
        renderCatalog();
        renderInvoiceItems();
        renderPayments();
    }
    
    // ===== CATALOG RENDERING =====
    function renderCatalog() {
        if (!catalogItems.length) {
            itemList.innerHTML = `<div class="empty-state"><div class="empty-state-icon">📦</div><p>No items</p></div>`;
        } else {
            itemList.innerHTML = catalogItems.map(item => `
                <li class="item-card" data-name="${item.name}" data-price="${item.price}">
                    <div class="item-info">
                        <h4>${item.name}</h4>
                        <span class="item-price">$${parseFloat(item.price).toFixed(2)}</span>
                    </div>
                    <button class="delete-item" data-name="${item.name}"><i class="fas fa-trash"></i></button>
                </li>
            `).join('');
            
            // Add click to add item to invoice
            itemList.querySelectorAll('.item-card').forEach(card => {
                card.addEventListener('click', (e) => {
                    if (e.target.closest('.delete-item')) {
                        e.stopPropagation();
                        const name = card.dataset.name;
                        deleteCatalogItem(name);
                        return;
                    }
                    const name = card.dataset.name;
                    const price = parseFloat(card.dataset.price);
                    invoiceItems.push({ name, price, quantity: 1 });
                    updateAll();
                    showToast(`${name} added to invoice`, 'success');
                });
            });
        }
        document.getElementById('item-count').textContent = `${catalogItems.length} items`;
    }
    
    async function deleteCatalogItem(name) {
        try {
            const response = await fetch('/api/ledger/invoices/delete-item', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name })
            });
            
            if (response.ok) {
                catalogItems = catalogItems.filter(i => i.name !== name);
                renderCatalog();
                showToast('Item deleted from catalog', 'info');
            }
        } catch (error) {
            console.error('Error deleting item:', error);
        }
    }
    
    // ===== INVOICE ITEMS RENDERING =====
    function renderInvoiceItems() {
        if (!invoiceItems.length) {
            invoiceItemsBody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:40px;">No items in invoice</td></tr>`;
        } else {
            let html = '';
            invoiceItems.forEach((item, index) => {
                const total = item.price * (item.quantity || 1);
                html += `
                <tr>
                    <td>${item.name}</td>
                    <td>${item.quantity || 1}</td>
                    <td>$${parseFloat(item.price).toFixed(2)}</td>
                    <td>$${total.toFixed(2)}</td>
                    <td><button class="btn btn-small btn-danger remove-item" data-index="${index}"><i class="fas fa-times"></i></button></td>
                </tr>`;
            });
            invoiceItemsBody.innerHTML = html;
            
            // Remove handlers
            document.querySelectorAll('.remove-item').forEach(btn => {
                btn.addEventListener('click', () => {
                    const idx = parseInt(btn.dataset.index);
                    invoiceItems.splice(idx, 1);
                    updateAll();
                    showToast('Item removed', 'info');
                });
            });
        }
        
        const totals = calculateTotals();
        subtotalSpan.textContent = `$${totals.subtotal.toFixed(2)}`;
        subtotalRef.textContent = `$${totals.subtotal.toFixed(2)}`;
        paidTotalSpan.textContent = `$${totals.paid.toFixed(2)}`;
        balanceDueSpan.textContent = `$${totals.balance.toFixed(2)}`;
    }
    
    async function togglePaymentStatus(paymentId) {
        const payment = payments.find(p => p.id === paymentId);
        if (!payment) return;
        
        const newStatus = payment.status === 'completed' ? 'pending' : 'completed';
        
        try {
            const response = await fetch('/api/ledger/invoices/update-payment-status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    payment_id: paymentId,
                    payment_status: newStatus
                })
            });
            
            if (response.ok) {
                await loadPayments();
                renderInvoiceItems();
                showToast('Payment status updated', 'success');
            } else {
                showToast('Error updating payment status', 'error');
            }
        } catch (error) {
            console.error('Error updating payment status:', error);
            showToast('Failed to update payment status', 'error');
        }
    }
    
    async function deletePayment(paymentId) {
        if (!confirm('Are you sure you want to delete this payment?')) return;
        
        try {
            const response = await fetch(`/api/ledger/invoices/payments/${paymentId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                await loadPayments();
                renderInvoiceItems();
                showToast('Payment deleted', 'success');
            } else {
                showToast('Error deleting payment', 'error');
            }
        } catch (error) {
            console.error('Error deleting payment:', error);
            showToast('Failed to delete payment', 'error');
        }
    }

    // ===== PAYMENTS RENDERING =====
    function renderPayments() {
        const invoicePayments = payments.filter(p => p.invoiceId === INVOICE_ID);
        paymentCount.textContent = `${invoicePayments.length} payment${invoicePayments.length !== 1 ? 's' : ''}`;
        
        if (!invoicePayments.length) {
            paymentList.innerHTML = `<div class="empty-state"><div class="empty-state-icon">💸</div><p>No payments recorded for this invoice</p></div>`;
        } else {
            let html = '';
            invoicePayments.sort((a,b) => (b.date || '').localeCompare(a.date || '')).forEach(p => {
                html += `
                <div class="payment-item">
                    <div class="payment-info">
                        <h4>$${p.amount.toFixed(2)} · ${p.method}</h4>
                        <div class="payment-meta">
                            <span>${p.date || 'n/a'}</span>
                            <span class="status-badge ${p.status}">${p.status}</span>
                        </div>
                    </div>
                    <div class="payment-actions">
                        <button class="toggle-payment" data-id="${p.id}" title="Toggle status"><i class="fas fa-sync-alt"></i></button>
                        <button class="delete-payment" data-id="${p.id}" title="Delete"><i class="fas fa-trash"></i></button>
                    </div>
                </div>`;
            });
            paymentList.innerHTML = html;
            
            // Toggle status
            paymentList.querySelectorAll('.toggle-payment').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const id = parseInt(btn.dataset.id);
                    await togglePaymentStatus(id);
                });
            });
            
            // Delete payment
            paymentList.querySelectorAll('.delete-payment').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const id = parseInt(btn.dataset.id);
                    await deletePayment(id);
                });
            });
        }
        
        // Update totals after payment changes
        const totals = calculateTotals();
        balanceDueSpan.textContent = `$${totals.balance.toFixed(2)}`;
        paidTotalSpan.textContent = `$${totals.paid.toFixed(2)}`;
    }
    
    // ===== ADD CATALOG ITEM =====
    addItemForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = newItemName.value.trim();
        const price = parseFloat(newItemPrice.value);
        if (!name || isNaN(price) || price <= 0) {
            showToast('Please enter valid item', 'warning');
            return;
        }
        
        try {
            const response = await fetch('/api/ledger/invoices/add-item', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, price })
            });
            
            if (response.ok) {
                catalogItems.push({ name, price });
                renderCatalog();
                addItemForm.reset();
                showToast('Item added to catalog', 'success');
            }
        } catch (error) {
            console.error('Error adding item:', error);
        }
    });
    
    // ===== RECORD PAYMENT =====
    recordBtn.addEventListener('click', () => {
        const amount = parseFloat(paymentAmount.value);
        if (isNaN(amount) || amount <= 0) {
            showToast('Enter valid amount', 'warning');
            return;
        }
        const method = paymentMethod.value;
        const status = paymentStatus.value;
        
        recordPayment(amount, method, status);
        paymentAmount.value = '';
    });
    
    // ===== SAVE INVOICE =====
    saveBtn.addEventListener('click', async () => {
        const totals = calculateTotals();
        const invoiceData = {
            items: invoiceItems,
            total: totals.subtotal,
            cfid: cfidInput.value ? parseInt(cfidInput.value) : null,
            details: {
                billing_name: billingName.value,
                billing_address: billingAddress.value,
                billing_email_address: billingEmail.value,
                billing_phone: billingPhone.value,
                billing_notes: billingNotes.value
            }
        };
        
        try {
            const response = await fetch('/api/ledger/invoices/save-invoice', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(invoiceData)
            });
            
            if (response.ok) {
                showToast('Invoice saved successfully', 'success');
            } else {
                showToast('Error saving invoice', 'error');
            }
        } catch (error) {
            console.error('Error saving invoice:', error);
            showToast('Error saving invoice', 'error');
        }
    });
    
    // ===== GENERATE PDF =====
    pdfBtn.addEventListener('click', () => {
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();
        
        doc.setFontSize(22);
        doc.setFont('helvetica', 'bold');
        doc.text('INVOICE', 20, 20);
        
        doc.setFontSize(11);
        doc.setFont('helvetica', 'normal');
        doc.text(`Invoice #: INV-${INVOICE_ID}`, 20, 30);
        doc.text(`Date: ${new Date().toISOString().slice(0,10)}`, 20, 35);
        
        // Billing
        doc.text(`Bill To: ${billingName.value}`, 20, 45);
        doc.text(`${billingAddress.value}`, 20, 52);
        doc.text(`Email: ${billingEmail.value}`, 20, 62);
        
        // Items summary
        let y = 80;
        doc.setFont('helvetica', 'bold');
        doc.text('Item', 20, y);
        doc.text('Qty', 100, y);
        doc.text('Total', 150, y);
        y += 8;
        doc.setFont('helvetica', 'normal');
        
        invoiceItems.forEach(item => {
            doc.text(item.name, 20, y);
            doc.text((item.quantity || 1).toString(), 100, y);
            doc.text(`$${(item.price * (item.quantity || 1)).toFixed(2)}`, 150, y);
            y += 8;
        });
        
        const totals = calculateTotals();
        y += 10;
        doc.setFont('helvetica', 'bold');
        doc.text(`Subtotal: $${totals.subtotal.toFixed(2)}`, 130, y);
        y += 8;
        doc.text(`Paid: $${totals.paid.toFixed(2)}`, 130, y);
        y += 8;
        doc.text(`Balance Due: $${totals.balance.toFixed(2)}`, 130, y);
        
        doc.save(`invoice-${INVOICE_ID}.pdf`);
        showToast('PDF generated', 'success');
    });
    
    // ===== TOAST =====
    function showToast(msg, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = msg;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 2500);
    }
    
    // ===== CFID AUTO-FILL =====
    cfidInput.addEventListener('input', () => {
        const cfid = cfidInput.value;
        // You might want to fetch CF details from an API here
        if (cfid === '1001') {
            billingName.value = 'Acme Corp';
            billingAddress.value = '123 Acme Ave, Tech City, 94105';
            billingEmail.value = 'billing@acme.com';
            billingPhone.value = '+1 555-1234';
        } else if (cfid === '1002') {
            billingName.value = 'Beta LLC';
            billingAddress.value = '456 Beta Street';
            billingEmail.value = 'hello@beta.io';
            billingPhone.value = '+1 555-2222';
        }
    });
    
    // ===== INIT =====
    async function init() {
        await loadInvoiceData();
        await loadCatalogItems();
        await loadPayments();
    }
    
    init();
})();