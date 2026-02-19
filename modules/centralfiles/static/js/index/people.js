const input = document.getElementById('name-input');
const list = document.getElementById('people-list');
const modal = document.getElementById('deleteModal');
const deletePersonNameSpan = document.getElementById('delete-person-name');
const cancelBtn = document.getElementById('cancel-delete');
const confirmBtn = document.getElementById('confirm-delete');
const openAddModalBtn = document.getElementById('open-add-modal-btn');
const addModal = document.getElementById('addPersonModal');
const cancelAddBtn = document.getElementById('cancel-add');
const confirmAddBtn = document.getElementById('confirm-add');
const isAliasCheckbox = document.getElementById('isAliasCheckbox');
const aliasFields = document.getElementById('aliasFields');
const standardNameFields = document.getElementById('standardNameFields');
const aliasNameInput = document.getElementById('aliasName');
const firstNameInput = document.getElementById('firstName');
const middleNameInput = document.getElementById('middleName');
const lastNameInput = document.getElementById('lastName');
const profileTypeSelect = document.getElementById('profileType');

let deletePersonData = { card: null, cfid: null, name: null };

// Close delete modal
function closeModal() {
  modal.style.display = 'none';
  deletePersonData = { card: null, cfid: null, name: null };
}

// Close add modal
function closeAddModal() {
  addModal.style.display = 'none';
  resetAddForm();
}

// Reset the add form
function resetAddForm() {
  isAliasCheckbox.checked = false;
  aliasNameInput.value = '';
  firstNameInput.value = '';
  middleNameInput.value = '';
  lastNameInput.value = '';
  profileTypeSelect.value = '';
  toggleAliasFields();
}

// Toggle between alias and standard name fields
function toggleAliasFields() {
  if (isAliasCheckbox.checked) {
    aliasFields.style.display = 'block';
    standardNameFields.style.display = 'none';
  } else {
    aliasFields.style.display = 'none';
    standardNameFields.style.display = 'block';
  }
}

// Validate the add form
function validateAddForm() {
  if (!profileTypeSelect.value) {
    alert('Please select a profile type');
    return false;
  }

  if (isAliasCheckbox.checked) {
    if (!aliasNameInput.value.trim()) {
      alert('Please enter an alias name');
      return false;
    }
  } else {
    if (!firstNameInput.value.trim()) {
      alert('Please enter a first name');
      return false;
    }
  }
  return true;
}

// Construct name based on form input
function constructName() {
  if (isAliasCheckbox.checked) {
    return aliasNameInput.value.trim();
  } else {
    const parts = [];
    if (firstNameInput.value.trim()) parts.push(firstNameInput.value.trim());
    if (middleNameInput.value.trim()) parts.push(middleNameInput.value.trim());
    if (lastNameInput.value.trim()) parts.push(lastNameInput.value.trim());
    return parts.join(' ');
  }
}

// Event listeners
modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });
cancelBtn.addEventListener('click', closeModal);

addModal.addEventListener('click', (e) => { if (e.target === addModal) closeAddModal(); });
cancelAddBtn.addEventListener('click', closeAddModal);

isAliasCheckbox.addEventListener('change', toggleAliasFields);

openAddModalBtn.addEventListener('click', () => {
  resetAddForm();
  addModal.style.display = 'flex';
});

confirmAddBtn.addEventListener('click', addName);

confirmBtn.addEventListener('click', async () => {
  if (deletePersonData.card && deletePersonData.cfid) {
    await deletePerson(deletePersonData.cfid, deletePersonData.card);
    closeModal();
  }
});

async function fetchJSON(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

function showEmptyState() {
  list.innerHTML = `<div class="empty-state"><div class="empty-icon">👤</div><p>No people found. Add someone to get started.</p></div>`;
}

async function get_name_is_staff(cfid) {
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

async function createPersonCard(name, cfid) {
  const container = document.createElement('div');
  container.className = 'person-card-container';
  container.dataset.cfid = cfid;
  container.dataset.name = name;
  const staffEmoji = await get_name_is_staff(cfid);
  container.innerHTML = `
    <a class="person-card" href="/files/get/${cfid ?? encodeURIComponent(name)}">
      <div class="person-card-content">
        <img class="profile-image" src="/api/files/${cfid}/profile_icon" alt="${name}" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48Y2lyY2xlIGN4PSIzMCIgY3k9IjMwIiByPSIzMCIgZmlsbD0iI2U5ZWNlZiIvPjxwYXRoIGQ9Ik0zMCAzM0MzMy4zMTM3IDMzIDM2IDMwLjMxMzcgMzYgMjdDMzYgMjMuNjg2MyAzMy4zMTM3IDIxIDMwIDIxQzI2LjY4NjMgMjEgMjQgMjMuNjg2MyAyNCAyN0MyNCAzMC4zMTM3IDI2LjY4NjMgMzMgMzAgMzNaIiBmaWxsPSIjNmM3NTdkIi8+PHBhdGggZD0iTTQyIDM5QzQyIDQxLjIwOTEgNDAuMjA5MSA0MyAzOCA0M0gyMkMxOS43OTA5IDQzIDE4IDQxLjIwOTEgMTggMzlDMTggMzQuNTgyNSAyNS4zNzIgMzIgMzAgMzJDMzQuNjI4IDMyIDQyIDM0LjU4MjUgNDIgMzlaIiBmaWxsPSIjNmM3NTdkIi8+PC9zdmc+'">
        <div class="person-info">
          <div class="person-name">${name}${staffEmoji}</div>
          <div class="person-occupation occupation-loading">Loading occupation...</div>
        </div>
      </div>
    </a>
    <button class="delete-btn" title="Delete ${name}">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
      </svg>
    </button>
  `;
  return container;
}

async function loadOccupation(card, cfid) {
  try {
    const res = await fetch(`/api/files/${cfid}/occupation`);
    const text = res.ok ? await res.text() : 'Occupation unavailable';
    const el = card.querySelector('.person-occupation');
    if (el) { el.textContent = text || '—'; el.classList.remove('occupation-loading'); }
  } catch { }
}

function showDeleteConfirmation(card) {
  deletePersonData = { card, cfid: card.dataset.cfid, name: card.dataset.name };
  deletePersonNameSpan.textContent = card.dataset.name;
  modal.style.display = 'flex';
}

async function deletePerson(cfid, cardEl) {
  try {
    const response = await fetch('/api/files/delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ cfid }) });
    const data = await response.json();
    if (data.success) {
      cardEl.remove();
      if (!list.querySelector('.person-card-container')) showEmptyState();
    } else {
      alert(data.error || 'Delete failed');
    }
  } catch (err) {
    alert('Error: ' + err.message);
  }
}

async function addName() {
  if (!validateAddForm()) return;
  
  const profileType = profileTypeSelect.value;
  
  // Prepare the post data according to CreateNamePostData structure
  let postData;
  
  if (isAliasCheckbox.checked) {
    // Alias case: only alias and profile_type
    postData = {
      alias: aliasNameInput.value.trim(),
      profile_type: profileType,
      first_name: null,
      middle_name: null,
      last_name: null
    };
  } else {
    // Standard name case: first_name (required), middle_name, last_name, and profile_type
    postData = {
      first_name: firstNameInput.value.trim() || null,
      middle_name: middleNameInput.value.trim() || null,
      last_name: lastNameInput.value.trim() || null,
      alias: null,
      profile_type: profileType
    };
  }
  
  // For dupecheck, we need to construct the full name for display purposes
  const displayName = constructName();
  
  try {
    const dupe = await fetch(`/files/dupecheck/${encodeURIComponent(displayName)}`).then(r => r.ok ? r.json() : { exists: false });
    if (dupe.exists) {
      if (!confirm(`Name exists (cfids: ${dupe.cfids}). Add anyway?`)) { 
        closeAddModal();
        return; 
      }
    }
    
    const data = await fetchJSON('/api/files/create', { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify(postData) 
    });
    
    if (data.success && data.cfid) {
      if (list.querySelector('.empty-state')) list.innerHTML = '';
      // Use displayName for the card, which will show the full constructed name
      const card = await createPersonCard(displayName, data.cfid);
      list.appendChild(card);
      loadOccupation(card, data.cfid);
      closeAddModal();
    } else alert('Server error: ' + (data.error || 'Unknown error'));
  } catch (err) {
    alert('Error adding: ' + err.message);
  }
}

async function Get_Names() {
  try {
    const data = await fetchJSON('/api/files/get_names');
    if (!Array.isArray(data.names) || data.names.length === 0) { showEmptyState(); return; }
    list.innerHTML = '';
    const fragment = document.createDocumentFragment();
    for (let i = 0; i < data.names.length; i++) {
      const card = await createPersonCard(data.names[i], data.cfids[i]);
      fragment.appendChild(card);
      loadOccupation(card, data.cfids[i]);
    }
    list.appendChild(fragment);
  } catch { showEmptyState(); }
}

// event delegation delete
list.addEventListener('click', (e) => {
  const btn = e.target.closest('.delete-btn');
  if (btn) {
    const card = btn.closest('.person-card-container');
    if (card) showDeleteConfirmation(card);
  }
});

window.filterNames = function() {
  const filter = document.getElementById('search-input').value.toLowerCase();
  const items = list.querySelectorAll('.person-card-container');
  let visibleCount = 0;
  items.forEach(item => {
    const name = item.dataset.name?.toLowerCase() || '';
    if (name.includes(filter)) { item.style.display = ''; visibleCount++; }
    else { item.style.display = 'none'; }
  });
  const counter = document.getElementById('people-counter');
  if (counter) counter.innerText = visibleCount + ' visible';
};

document.addEventListener('DOMContentLoaded', () => {
  Get_Names();
});