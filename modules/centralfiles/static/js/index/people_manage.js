// noinspection JSUnresolvedReference,ExceptionCaughtLocallyJS

const input = document.getElementById('name-input');
const list = document.getElementById('people-list');

// Create modal elements
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

let personToDelete = null;

// Modal event listeners
document.getElementById('cancel-delete').addEventListener('click', () => {
  modal.style.display = 'none';
  personToDelete = null;
});

document.getElementById('confirm-delete').addEventListener('click', async () => {
  if (personToDelete) {
    await deletePerson(personToDelete.name, personToDelete.cfid, personToDelete.card);
  }
  modal.style.display = 'none';
  personToDelete = null;
});

// Close modal when clicking outside
modal.addEventListener('click', (e) => {
  if (e.target === modal) {
    modal.style.display = 'none';
    personToDelete = null;
  }
});

async function Get_Names() {
    try {
        const response = await fetch('/api/files/get_names');
        if (!response.ok) throw new Error(`Network response was not ok (${response.status})`);
        const data = await response.json();

        if (Array.isArray(data.names) && Array.isArray(data.cfids)) {
            if (data.names.length !== data.cfids.length) {
                console.warn('Mismatched names and cfids lengths');
                return;
            }
            list.innerHTML = ''; // Clear the list before adding
            
            // Add each person card
            for (let i = 0; i < data.names.length; i++) {
                await addNameToDOM(data.names[i], data.cfids[i]);
            }
            
            // Show empty state if no people
            if (data.names.length === 0) {
                showEmptyState();
            }
        } else {
            console.warn('Unexpected data format:', data);
            showEmptyState();
        }
    } catch (error) {
        console.error('Error fetching names:', error);
        showEmptyState();
    }
}

function showEmptyState() {
    list.innerHTML = `
        <div class="empty-state">
            <div class="empty-icon">🔍</div>
            <p>No people found. Add someone to get started.</p>
        </div>
    `;
}

async function addNameToDOM(name, cfid) {
    const card = document.createElement('div');
    card.className = 'person-card-container';
    
    // Create card content structure
    card.innerHTML = `
        <a class="person-card" href="/files/get/${cfid !== null ? cfid : name}">
            <div class="person-card-content">
                <img class="profile-image" src="/api/files/${cfid}/profile_icon" alt="${name}" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMzAiIGN5PSIzMCIgcj0iMzAiIGZpbGw9IiNlOWVjZWYiLz4KPHBhdGggZD0iTTMwIDMzQzMzLjMxMzcgMzMgMzYgMzAuMzEzNyAzNiAyN0MzNiAyMy42ODYzIDMzLjMxMzcgMjEgMzAgMjFDMjYuNjg2MyAyMSAyNCAyMy42ODYzIDI0IDI3QzI0IDMwLjMxMzcgMjYuNjg2MyAzMyAzMCAzM1oiIGZpbGw9IiM2Yzc1N2QiLz4KPHBhdGggZD0iTTQyIDM5QzQyIDQxLjIwOTEgNDAuMjA5MSA0MyAzOCA0M0gyMkMxOS43OTA5IDQzIDE4IDQxLjIwOTEgMTggMzlDMTggMzQuNTgyNSAyNS4zNzIgMzIgMzAgMzJDMzQuNjI4IDMyIDQyIDM0LjU4MjUgNDIgMzlaIiBmaWxsPSIjNmM3NTdkIi8+Cjwvc3ZnPgo='">
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
    
    list.appendChild(card);
    
    // Add event listener to delete button
    const deleteBtn = card.querySelector('.delete-btn');
    deleteBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        showDeleteConfirmation(name, cfid, card);
    });
    
    // Load occupation data
    await loadOccupation(card, cfid);
}

function showDeleteConfirmation(name, cfid, card) {
    personToDelete = { name, cfid, card };
    document.getElementById('delete-person-name').textContent = name;
    modal.style.display = 'flex';
}

async function deletePerson(name, cfid, card) {
    try {
        const response = await fetch('/api/files/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });

        if (!response.ok) {
            alert('Failed to delete name on server');
            return;
        }

        const data = await response.json();
        if (data.success) {
            // Remove from DOM
            card.remove();
            
            // Show empty state if no people left
            if (list.children.length === 0) {
                showEmptyState();
            }
        } else {
            alert('Server failed to delete name');
        }
    } catch (error) {
        console.error('Error deleting name:', error);
        alert('Error deleting name');
    }
}

async function loadOccupation(card, cfid) {
    try {
        const response = await fetch(`/api/files/${cfid}/occupation`);
        if (response.ok) {
            // Occupation endpoint now returns HTMLResponse with plain text
            const occupationText = await response.text();
            const occupationElement = card.querySelector('.person-occupation');
            occupationElement.textContent = occupationText || 'No occupation set';
            occupationElement.classList.remove('occupation-loading');
        } else {
            throw new Error(`Failed to load occupation: ${response.status}`);
        }
    } catch (error) {
        console.error(`Error loading occupation for ${cfid}:`, error);
        const occupationElement = card.querySelector('.person-occupation');
        occupationElement.textContent = 'Occupation unavailable';
        occupationElement.classList.remove('occupation-loading');
    }
}

async function addName() {
    const name = input.value.trim();
    if (!name) return;

    try {
        // Check for duplicate before creating
        const dupeCheckResp = await fetch(`/files/dupecheck/${encodeURIComponent(name)}`);
        if (dupeCheckResp.ok) {
            const dupeData = await dupeCheckResp.json();
            if (dupeData.exists) {
                let proceed = confirm('A profile with this name already exists (cfids: ' + dupeData.cfids + ').\nProceed anyway?');
                if (!proceed) {
                    input.value = '';
                    return;
                }
            }
        } else if (dupeCheckResp.status !== 404) {
            if (dupeCheckResp.status === 500) {
                alert('Something went wrong while checking for duplicates.');
                console.warn('Error checking for duplicates:', dupeCheckResp.statusText);
                return;
            }
        }

        const response = await fetch('/api/files/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });

        if (!response.ok) {
            alert('Failed to create name on server');
            return;
        }

        const data = await response.json();
        if (data.success && data.cfid) {
            // Remove empty state if it exists
            const emptyState = list.querySelector('.empty-state');
            if (emptyState) {
                emptyState.remove();
            }
            
            await addNameToDOM(name, data.cfid);
            input.value = '';
        } else {
            alert('Server failed to create name');
        }
    } catch (error) {
        console.error('Error adding name:', error);
        alert('Error adding name');
    }
}

// Remove the old removeName function since we're using individual delete buttons
document.addEventListener('DOMContentLoaded', Get_Names);