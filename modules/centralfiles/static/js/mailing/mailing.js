// State management
let people = [];
let selectedPeople = new Set(); // Store emails as identifiers
let originalPeople = []; // Keep original for search filtering

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    // Load actual people from database
    Get_Names();
    
    // Set up event listeners
    setupEventListeners();
});

function setupEventListeners() {

    // Select/Deselect all
    document.getElementById('selectAllBtn').addEventListener('click', selectAll);
    document.getElementById('clearSelectionBtn').addEventListener('click', clearSelection);

    // Clear form button
    document.getElementById('clearBtn').addEventListener('click', clearForm);

    // Mail form submission
    document.getElementById('mailForm').addEventListener('submit', sendBulkMail);

    // Character counters
    document.getElementById('subject').addEventListener('input', updateSubjectCount);
    document.getElementById('message').addEventListener('input', updateMessageCount);

    // Delete modal
    document.getElementById('cancel-delete').addEventListener('click', hideDeleteModal);
    document.getElementById('confirm-delete').addEventListener('click', confirmDelete);
    
    // Close modal when clicking outside
    window.addEventListener('click', function(e) {
        if (e.target.classList.contains('delete-modal')) {
            hideDeleteModal();
        }
    });
}

// Helper function for fetching JSON (from people.js)
async function fetchJSON(url, options) {
    const res = await fetch(url, options);
    if (!res.ok) throw new Error(res.statusText);
    return res.json();
}

// Get is_staff indicator (from people.js)
async function getNameIsStaff(cfid) {
    try {
        const res = await fetch(`/api/files/${cfid}/is_staff`);
        if (res.ok) {
            const d = await res.json();
            return d.is_staff ? " 🛡️" : "";
        }
        return "";
    } catch {
        return "";
    }
}

// Load occupation for a person (from people.js)
async function loadOccupation(cfid, personObj) {
    try {
        const res = await fetch(`/api/files/${cfid}/occupation`);
        const text = res.ok ? await res.text() : 'Occupation unavailable';
        personObj.occupation = text || '—';
    } catch {
        personObj.occupation = 'Occupation unavailable';
    }
}

// Get email for a person (you may need to adjust this endpoint)
async function getPersonEmail(cfid) {
    try {
        // Try to get email - you might have a different endpoint
        const res = await fetch(`/api/files/${cfid}/email`);
        if (res.ok) {
            return await res.text();
        }
        // Fallback: generate email from name
        return null;
    } catch {
        return null;
    }
}

// Load actual people from database (adapted from people.js)
async function Get_Names() {
    try {
        const data = await fetchJSON('/api/files/get_names');
        if (!Array.isArray(data.names) || data.names.length === 0) {
            showEmptyState();
            return;
        }
        
        // Clear existing people
        people = [];
        
        // Build people array with cfids
        for (let i = 0; i < data.names.length; i++) {
            const name = data.names[i];
            const cfid = data.cfids[i];
            
            // Get staff indicator
            const staffEmoji = await getNameIsStaff(cfid);
            
            // Try to get email
            let email = await getPersonEmail(cfid);
            if (!email) {
                // Generate a placeholder email if none exists
                email = generateEmail(name);
            }
            
            // Create person object
            const person = {
                name: name + staffEmoji,
                rawName: name,
                cfid: cfid,
                email: email,
                occupation: 'Loading...'
            };
            
            people.push(person);
            
            // Load occupation asynchronously
            loadOccupation(cfid, person).then(() => {
                renderPeopleList();
            });
        }
        
        originalPeople = [...people];
        renderPeopleList();
        
    } catch (error) {
        console.error('Error loading people:', error);
        showEmptyState();
    }
}

function showEmptyState() {
    const container = document.getElementById('people-list');
    container.innerHTML = `
        <div class="empty-state small">
            <div class="empty-icon">👤</div>
            <p>No people found. Add someone to get started.</p>
        </div>
    `;
}

function generateEmail(name) {
    // Remove any emoji/staff indicators and generate email
    const cleanName = name.replace(/[🛡️]/g, '').trim();
    return cleanName.toLowerCase().replace(/\s+/g, '.') + '@example.com';
}

function getCfidFromPath() {
    // Try to get from URL path
    const pathParts = window.location.pathname.split('/');
    // Look for a numeric part that might be the cfid
    for (const part of pathParts) {
        if (/^\d+$/.test(part)) {
            return part;
        }
    }
    return null;
}

function filterNames() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    
    if (!searchTerm) {
        people = [...originalPeople];
    } else {
        people = originalPeople.filter(person => 
            person.name.toLowerCase().includes(searchTerm) ||
            (person.occupation && person.occupation.toLowerCase().includes(searchTerm)) ||
            (person.email && person.email.toLowerCase().includes(searchTerm))
        );
    }
    
    renderPeopleList();
}

function renderPeopleList() {
    const container = document.getElementById('people-list');
    
    if (people.length === 0) {
        container.innerHTML = `
            <div class="empty-state small">
                <div class="empty-icon">👤</div>
                <p>No people match your search.</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    people.forEach((person, index) => {
        const isSelected = selectedPeople.has(person.email);
        const selectedClass = isSelected ? 'selected' : '';
        const occupationClass = person.occupation === 'Loading...' ? 'occupation-loading' : '';
        
        html += `
            <div class="person-card-container ${selectedClass}" data-cfid="${person.cfid}" data-person-email="${person.email}">
                <input type="checkbox" class="person-checkbox" 
                        ${isSelected ? 'checked' : ''} 
                        onchange="togglePersonSelection('${person.email}', ${index})">
                <div class="person-card-content" onclick="togglePersonSelection('${person.email}', ${index})">
                    <img class="profile-image small" src="/api/files/${person.cfid}/profile_icon" 
                         alt="${escapeHtml(person.rawName)}" 
                         onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48Y2lyY2xlIGN4PSIzMCIgY3k9IjMwIiByPSIzMCIgZmlsbD0iI2U5ZWNlZiIvPjxwYXRoIGQ9Ik0zMCAzM0MzMy4zMTM3IDMzIDM2IDMwLjMxMzcgMzYgMjdDMzYgMjMuNjg2MyAzMy4zMTM3IDIxIDMwIDIxQzI2LjY4NjMgMjEgMjQgMjMuNjg2MyAyNCAyN0MyNCAzMC4zMTM3IDI2LjY4NjMgMzMgMzAgMzNaIiBmaWxsPSIjNmM3NTdkIi8+PHBhdGggZD0iTTQyIDM5QzQyIDQxLjIwOTEgNDAuMjA5MSA0MyAzOCA0M0gyMkMxOS43OTA5IDQzIDE4IDQxLjIwOTEgMTggMzlDMTggMzQuNTgyNSAyNS4zNzIgMzIgMzAgMzJDMzQuNjI4IDMyIDQyIDM0LjU4MjUgNDIgMzlaIiBmaWxsPSIjNmM3NTdkIi8+PC9zdmc+'">
                    <div class="person-info">
                        <div class="person-name small">${escapeHtml(person.name)}</div>
                        <div class="person-occupation small ${occupationClass}">${escapeHtml(person.occupation)}</div>
                        <div class="person-email small" style="font-size: 0.7rem; color: var(--text-soft);">${escapeHtml(person.email)}</div>
                    </div>
                </div>
                <button class="delete-btn small" onclick="showDeleteModal('${escapeHtml(person.rawName)}', ${person.cfid}, ${index})">✕</button>
            </div>
        `;
    });
    
    container.innerHTML = html;
    updateSelectionStats();
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function togglePersonSelection(email, index) {
    if (!email) return;
    
    if (selectedPeople.has(email)) {
        selectedPeople.delete(email);
    } else {
        selectedPeople.add(email);
    }
    
    renderPeopleList();
    updateRecipientSummary();
}

function selectAll() {
    people.forEach(person => {
        if (person.email) {
            selectedPeople.add(person.email);
        }
    });
    renderPeopleList();
    updateRecipientSummary();
}

function clearSelection() {
    selectedPeople.clear();
    renderPeopleList();
    updateRecipientSummary();
}

function updateSelectionStats() {
    const stats = document.getElementById('selectionStats');
    stats.textContent = `${selectedPeople.size} selected`;
}

function updateRecipientSummary() {
    const summary = document.getElementById('recipientSummary');
    const count = document.getElementById('selectedCount');
    const badgesContainer = document.getElementById('selectedRecipientsList');
    
    const selectedCount = selectedPeople.size;
    count.textContent = selectedCount;
    
    if (selectedCount === 0) {
        summary.textContent = 'No recipients selected';
        badgesContainer.innerHTML = '<span style="color: var(--text-soft);">None selected</span>';
    } else {
        summary.textContent = `${selectedCount} recipient(s) selected`;
        
        // Create badges
        let badgesHtml = '';
        people.forEach(person => {
            if (selectedPeople.has(person.email)) {
                badgesHtml += `
                    <span class="recipient-badge">
                        ${escapeHtml(person.rawName || person.name)}
                        <button class="remove-badge" onclick="removeRecipient('${person.email}')">✕</button>
                    </span>
                `;
            }
        });
        badgesContainer.innerHTML = badgesHtml;
    }
}

function removeRecipient(email) {
    if (selectedPeople.has(email)) {
        selectedPeople.delete(email);
        renderPeopleList();
        updateRecipientSummary();
    }
}

function updateSubjectCount() {
    const subject = document.getElementById('subject');
    const count = document.getElementById('subjectCount');
    count.textContent = `${subject.value.length}/100`;
}

function updateMessageCount() {
    const message = document.getElementById('message');
    const count = document.getElementById('messageCount');
    count.textContent = `${message.value.length}/5000`;
}

function clearForm() {
    document.getElementById('subject').value = '';
    document.getElementById('message').value = '';
    document.getElementById('subjectCount').textContent = '0/100';
    document.getElementById('messageCount').textContent = '0/5000';
    clearSelection();
    showStatus('Form cleared', 'info');
}

async function sendBulkMail(event) {
    event.preventDefault();
    
    const subject = document.getElementById('subject').value.trim();
    const message = document.getElementById('message').value.trim();
    
    if (!confirm("Send emails?")) {
        return
    }

    // Validate form
    if (selectedPeople.size === 0) {
        showStatus('Please select at least one recipient', 'error');
        return;
    }
    if (!subject) {
        showStatus('Please enter a subject', 'error');
        return;
    }
    if (!message) {
        showStatus('Please enter a message', 'error');
        return;
    }
    
    // Build array of recipient objects
    const recipients = [];
    people.forEach(person => {
        if (selectedPeople.has(person.email)) {
            recipients.push({
                email_address: person.email,
                subject_line: subject,
                message: message
            });
        }
    });

    // Show loading state
    const sendBtn = document.getElementById('sendEmailBtn');
    const originalText = sendBtn.innerHTML;
    sendBtn.innerHTML = '<i>⏳</i> Sending...';
    sendBtn.disabled = true;
    
    try {
        // Grab cfid from URL path (if needed)
        const cfid = getCfidFromPath();
        
        // Send POST request
        const response = await fetch(`/api/files/mail/bulksend`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ recipients })
        });
        
        if (response.ok) {
            const result = await response.text();
            if (result === 'true') {
                showStatus(`Email sent successfully to ${recipients.length} recipient(s)!`, 'success');
                clearForm();
            } else {
                showStatus('Failed to send emails', 'error');
            }
        } else if (response.status === 404) {
            showStatus('Error: Bulk mail endpoint not found.', 'error');
        } else {
            const errorText = await response.text();
            showStatus(`Error: ${errorText}`, 'error');
        }
    } catch (error) {
        console.error('Error sending email:', error);
        showStatus('Network error. Please try again.', 'error');
    } finally {
        sendBtn.innerHTML = originalText;
        sendBtn.disabled = false;
    }
}

function showStatus(message, type = 'info') {
    const statusEl = document.getElementById('status');
    statusEl.textContent = message;
    statusEl.className = `status-message ${type}`;
    statusEl.style.display = 'block';
    
    // Auto hide after 5 seconds for success/info
    if (type !== 'error') {
        setTimeout(() => {
            statusEl.style.display = 'none';
        }, 5000);
    }
}

// Delete functionality (adapted from people.js)
let personToDelete = null;

function showDeleteModal(name, cfid, index) {
    personToDelete = { name, cfid, index };
    document.getElementById('delete-person-name').textContent = name;
    document.getElementById('deleteModal').style.display = 'flex';
}

function hideDeleteModal() {
    document.getElementById('deleteModal').style.display = 'none';
    personToDelete = null;
}

async function confirmDelete() {
    if (personToDelete) {
        try {
            const response = await fetch('/api/files/delete', { 
                method: 'POST', 
                headers: { 'Content-Type': 'application/json' }, 
                body: JSON.stringify({ cfid: personToDelete.cfid }) 
            });
            const data = await response.json();
            
            if (data.success) {
                // Remove from arrays
                people.splice(personToDelete.index, 1);
                originalPeople = originalPeople.filter(p => p.cfid !== personToDelete.cfid);
                
                // Remove from selected if present
                const person = people[personToDelete.index];
                if (person && person.email) {
                    selectedPeople.delete(person.email);
                }
                
                renderPeopleList();
                updateRecipientSummary();
                showStatus(`Removed "${personToDelete.name}" from directory`, 'info');
            } else {
                alert(data.error || 'Delete failed');
            }
        } catch (err) {
            alert('Error: ' + err.message);
        }
        hideDeleteModal();
    }
}

// Expose functions to global scope for onclick handlers
window.filterNames = filterNames;
window.togglePersonSelection = togglePersonSelection;
window.showDeleteModal = showDeleteModal;
window.removeRecipient = removeRecipient;