// noinspection JSUnresolvedReference,ExceptionCaughtLocallyJS

const input = document.getElementById('name-input');
const list = document.getElementById('people-list');

// Create and append modal once
const modal = document.createElement('div');
modal.className = 'delete-modal';
modal.innerHTML = `
  <div class="modal-content">
    <h3>Confirm Deletion</h3>
    <p>Are you sure you want to delete <span id="delete-person-name"></span>?</p>
    <div class="modal-actions">
      <button class="btn btn-secondary" id="cancel-delete">Cancel</button>
      <button class="btn btn-danger" id="confirm-delete">Delete</button>
    </div>
  </div>
`;
document.body.appendChild(modal);

const deletePersonData = { card: null, name: null, cfid: null };

// Modal event listeners
modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
});
document.getElementById('cancel-delete').addEventListener('click', closeModal);
document.getElementById('confirm-delete').addEventListener('click', async () => {
    if (deletePersonData.card && deletePersonData.cfid && deletePersonData.name) {
        await deletePerson(deletePersonData.name, deletePersonData.cfid, deletePersonData.card);
        closeModal();
    }
});

function closeModal() {
    modal.style.display = 'none';
    deletePersonData.card = deletePersonData.name = deletePersonData.cfid = null;
}

// Helper for fetch with JSON
async function fetchJSON(url, options) {
    const res = await fetch(url, options);
    if (!res.ok) throw new Error(res.statusText);
    return res.json();
}

// Show empty state
function showEmptyState() {
    list.innerHTML = `
        <div class="empty-state">
            <div class="empty-icon">\U0001f50d</div>
            <p>No people found. Add someone to get started.</p>
        </div>
    `;
}

// Build a single person card
function createPersonCard(name, cfid) {
    const cardContainer = document.createElement('div');
    cardContainer.className = 'person-card-container';
    cardContainer.dataset.cfid = cfid;
    cardContainer.dataset.name = name;

    cardContainer.innerHTML = `
        <a class="person-card" href="/files/get/${cfid ?? encodeURIComponent(name)}">
            <div class="person-card-content">
                <img class="profile-image" src="/api/files/${cfid}/profile_icon" alt="${name}"
                     onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMzAiIGN5PSIzMCIgcj0iMzAiIGZpbGw9IiNlOWVjZWYiLz4KPHBhdGggZD0iTTMwIDMzQzMzLjMxMzcgMzMgMzYgMzAuMzEzNyAzNiAyN0MzNiAyMy42ODYzIDMzLjMxMzcgMjEgMzAgMjFDMjYuNjg2MyAyMSAyNCAyMy42ODYzIDI0IDI3QzI0IDMwLjMxMzcgMjYuNjg2MyAzMyAzMCAzM1oiIGZpbGw9IiM2Yzc1N2QiLz4KPHBhdGggZD0iTTQyIDM5QzQyIDQxLjIwOTEgNDAuMjA5MSA0MyAzOCA0M0gyMkMxOS43OTA5IDQzIDE4IDQxLjIwOTEgMTggMzlDMTggMzQuNTgyNSAyNS4zNzIgMzIgMzAgMzJDMzQuNjI4IDMyIDQyIDM0LjU4MjUgNDIgMzlaIiBmaWxsPSIjNmM3NTdkIi8+Cjwvc3ZnPgo='">
                <div class="person-info">
                    <div class="person-name">${name}</div>
                    <div class="person-occupation occupation-loading">Loading occupation...</div>
                </div>
            </div>
        </a>
        <button class="delete-btn" title="Delete ${name}">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
        </button>
    `;
    return cardContainer;
}

// Load occupations asynchronously without blocking DOM
async function loadOccupation(card, cfid) {
    try {
        const text = await fetch(`/api/files/${cfid}/occupation`).then(r => r.ok ? r.text() : 'Occupation unavailable');
        const el = card.querySelector('.person-occupation');
        el.textContent = text || 'No occupation set';
        el.classList.remove('occupation-loading');
    } catch {
        const el = card.querySelector('.person-occupation');
        el.textContent = 'Occupation unavailable';
        el.classList.remove('occupation-loading');
    }
}

// Show delete modal
function showDeleteConfirmation(card) {
    deletePersonData.card = card;
    deletePersonData.cfid = card.dataset.cfid;
    deletePersonData.name = card.dataset.name;
    document.getElementById('delete-person-name').textContent = deletePersonData.name;
    modal.style.display = 'flex';
}

// Delete person API
async function deletePerson(name, cfid, card) {
    try {
        const data = await fetchJSON('/api/files/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });

        if (data.success) {
            card.remove();
            if (!list.querySelector('.person-card-container')) showEmptyState();
        } else {
            alert('Server failed to delete name');
        }
    } catch (err) {
        console.error('Error deleting name:', err);
        alert('Error deleting name');
    }
}

// Add person both DOM + API
async function addName() {
    const name = input.value.trim();
    if (!name) return;

    try {
        // Check duplicates
        const dupeData = await fetch(`/files/dupecheck/${encodeURIComponent(name)}`)
            .then(r => r.ok ? r.json() : { exists: false });
        if (dupeData.exists) {
            const proceed = confirm(`A profile with this name already exists (cfids: ${dupeData.cfids}). Proceed anyway?`);
            if (!proceed) { input.value = ''; return; }
        }

        // Create person
        const data = await fetchJSON('/api/files/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });

        if (data.success && data.cfid) {
            if (list.querySelector('.empty-state')) list.querySelector('.empty-state').remove();
            const card = createPersonCard(name, data.cfid);
            list.appendChild(card);
            loadOccupation(card, data.cfid);
            input.value = '';
        } else {
            alert('Server failed to create name');
        }
    } catch (err) {
        console.error('Error adding name:', err);
        alert('Error adding name');
    }
}

// Fetch & render all names
async function Get_Names() {
    try {
        const data = await fetchJSON('/api/files/get_names');
        if (!Array.isArray(data.names) || !Array.isArray(data.cfids) || data.names.length !== data.cfids.length) {
            showEmptyState();
            return;
        }

        list.innerHTML = '';
        if (data.names.length === 0) return showEmptyState();

        const fragment = document.createDocumentFragment();
        data.names.forEach((name, i) => {
            const card = createPersonCard(name, data.cfids[i]);
            fragment.appendChild(card);
            loadOccupation(card, data.cfids[i]);
        });
        list.appendChild(fragment);
    } catch (err) {
        console.error('Error fetching names:', err);
        showEmptyState();
    }
}

// Event delegation for delete buttons
list.addEventListener('click', (e) => {
    if (e.target.closest('.delete-btn')) {
        const card = e.target.closest('.person-card-container');
        showDeleteConfirmation(card);
    }
});

// Initialize
document.addEventListener('DOMContentLoaded', Get_Names);
document.querySelector('.btn-primary').addEventListener('click', addName);
