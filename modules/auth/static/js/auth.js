async function fetchUserData() {
  const res = await fetch('/api/auth/userlist');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/* Toast handler */
function showToast(message, type = 'error') {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.className = `toast show ${type}`;
  setTimeout(() => {
    toast.className = 'toast';
  }, 4000);
}

function createUserCard(username, info, validPerms) {
  const card = document.createElement('div');
  card.classList.add('user-card');

  const header = document.createElement('div');
  header.classList.add('user-header');
  header.innerHTML = `
    <div>
      <h2>${username}</h2>
      <span class="status ${info.arrested ? 'arrested' : 'free'}">
        ${info.arrested ? 'Arrested' : 'Free'}
      </span>
    </div>
  `;
  card.appendChild(header);

  // Action buttons
  const actions = document.createElement('div');
  actions.classList.add('actions');

  const arrestBtn = document.createElement('button');
  arrestBtn.textContent = info.arrested ? 'Release' : 'Arrest';
  arrestBtn.className = info.arrested ? 'btn release' : 'btn arrest';
  actions.appendChild(arrestBtn);

  arrestBtn.addEventListener('click', async () => {
    const confirmText = info.arrested ? `Release ${username}?` : `Arrest ${username}?`;
    if (!confirm(confirmText)) return;

    const url = info.arrested
      ? `/api/auth/release/${encodeURIComponent(username)}`
      : `/api/auth/arrest/${encodeURIComponent(username)}`;

    try {
      const res = await fetch(url, { method: 'GET' });
      if (!res.ok) {
        const data = await res.json();
        const errText = data['error']
        showToast(errText || `Server error: ${res.status}`);
        return;
      }
      info.arrested = !info.arrested;

      // UI updates
      arrestBtn.textContent = info.arrested ? 'Release' : 'Arrest';
      arrestBtn.className = info.arrested ? 'btn release' : 'btn arrest';
      header.querySelector('.status').textContent = info.arrested ? 'Arrested' : 'Free';
      header.querySelector('.status').className = `status ${info.arrested ? 'arrested' : 'free'}`;
    } catch (err) {
      console.error(err);
      showToast('Failed to update arrest status.');
    }
  });

  card.appendChild(actions);

  // Permissions
  const permContainer = document.createElement('div');
  permContainer.classList.add('permissions');

  validPerms.forEach(perm => {
    const permRow = document.createElement('div');
    permRow.classList.add('permission-row');

    const label = document.createElement('label');
    label.textContent = perm;

    const toggle = document.createElement('input');
    toggle.type = 'checkbox';
    toggle.checked = !!info.permissions[perm];
    toggle.classList.add('toggle');

    toggle.addEventListener('change', async () => {
      const newVal = toggle.checked ? true : false;
      const url = `/api/auth/perm/set/${encodeURIComponent(username)}/${encodeURIComponent(perm)}/${newVal}`;
      try {
        const res = await fetch(url, { method: 'GET' });
        if (!res.ok) {
          const data = await res.json();
          const errText = data['error']
          showToast(errText || `Server error: ${res.status}`);
          toggle.checked = !toggle.checked;
        }
      } catch (err) {
        console.error(err);
        toggle.checked = !toggle.checked;
        showToast('Failed to update permission.');
      }
    });

    permRow.append(label, toggle);
    permContainer.appendChild(permRow);
  });

  card.appendChild(permContainer);
  return card;
}

async function loadUsers() {
  const container = document.getElementById('userGrid');
  container.innerHTML = '<div class="loading">Loading users...</div>';
  try {
    const { valid_permissions, users } = await fetchUserData();
    container.innerHTML = '';
    for (const [username, info] of Object.entries(users)) {
      container.appendChild(createUserCard(username, info, valid_permissions));
    }
  } catch (err) {
    container.innerHTML = '<div class="error">Failed to load user data.</div>';
    console.error(err);
    showToast('Failed to load user list.');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadUsers();

  // Back button
  document.getElementById('backBtn').addEventListener('click', () => {
    window.location.href = '/';
  });

  // Theme toggle
  const themeBtn = document.getElementById('themeToggle');
  const body = document.body;

  // Restore theme from localStorage
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme === 'light') {
    body.classList.add('light');
    themeBtn.textContent = '🌙 Dark Mode';
  }

  themeBtn.addEventListener('click', () => {
    body.classList.toggle('light');
    const isLight = body.classList.contains('light');
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
    themeBtn.textContent = isLight ? '🌙 Dark Mode' : '☀️ Light Mode';
  });
});
