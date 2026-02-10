// ===== Global Variables & State =====
let currentTab = 'auth';
let currentUsers = {};
let validPermissions = [];

// ===== Permission Icons Mapping =====
const PERMISSION_ICONS = {
    // Auth/Admin permissions
    'admin_panel': '🛡️',
    'perms_manage': '🔐',

    // Other
    'central_files': '📁',
    'bulletin_archives': '🗒️', 
    'ftp_server': '☁️',
    'dianetics': '🔺',
    'battleplans': '🎯',

    // Finances
    'accounts_view': '📒',
    'accounts_add': '📒',
    'accounts_delete': '📒',
    'accounts_add_transaction': '📒',
    'accounts_del_transaction': '📒',
    
    'invoices_view': '🧾',
    'invoices_create': '🧾',
    'invoices_delete': '🧾',
    'invoices_modify': '🧾',

    'debt_viewing': '💸',
    'debt_editting': '💸',

    'FP_view': '💳',
    'FP_edit': '💳',
    'odometering': '🛞',

    // System
    'app_logs': '📋',
    'app_settings': '💾',
};

// ===== Permission Categories =====
const PERMISSION_CATEGORIES = {
    'Management': ['central_files', 'battleplans', 'dianetics'],
    'Finances': [
        'accounts_view', 'accounts_add', 'accounts_delete', 'accounts_add_transaction', 'accounts_del_transaction',
        'invoices_view', 'invoices_create', 'invoices_delete', 'invoices_modify',
        'debt_viewing', 'debt_editting',
        'FP_edit', 'FP_view',
        'odometering',
        'ledger'
    ],
    'System': ['app_logs', 'admin_panel', 'app_settings', 'perms_manage'],
    'Other': ['bulletin_archives', 'ftp_server'],
};

// ===== PLACE-SAVING =====
const TAB_MEMORY_KEY = 'lastSelectedTab';
const TAB_MEMORY_TIME_KEY = 'lastSelectedTabTime';
const TAB_MEMORY_DURATION = 30 * 60 * 1000; // 30 minutes in ms

// ===== Tab Management =====
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === tabName + 'Tab');
    });
    
    // Update UI elements
    currentTab = tabName;
    const tabNames = {
        'auth': 'Staff Management',
        'settings': 'System Settings'
    };
    
    document.getElementById('currentTabIndicator').textContent = 
        `Currently viewing: ${tabNames[tabName]}`;
    
    // Load data for the tab if needed
    if (tabName === 'auth') {
        loadUsers();
    } else if (tabName === 'settings') {
        loadSettings();
    }

    // Remember selected tab with timestamp
    localStorage.setItem(TAB_MEMORY_KEY, tabName);
    localStorage.setItem(TAB_MEMORY_TIME_KEY, Date.now().toString());
}

// ===== Auth Management Functions =====
async function fetchUserData() {
    try {
        const res = await fetch('/api/knowledge/userlist');
        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            throw new Error(data.error || `HTTP ${res.status}`);
        }
        return await res.json();
    } catch (err) {
        console.error('Error fetching user data:', err);
        showToast(`Failed to load users: ${err.message}`, 'error');
        throw err;
    }
}

// ===== Helper: Group Permissions by Category =====
function groupPermissionsByCategory() {
    const grouped = {};
    
    validPermissions.forEach(perm => {
        let foundCategory = 'Other';
        
        // Find which category this permission belongs to
        Object.entries(PERMISSION_CATEGORIES).forEach(([category, perms]) => {
            if (perms.includes(perm)) {
                foundCategory = category;
            }
        });
        
        if (!grouped[foundCategory]) {
            grouped[foundCategory] = [];
        }
        
        if (!grouped[foundCategory].includes(perm)) {
            grouped[foundCategory].push(perm);
        }
    });
    
    return grouped;
}

// ===== Helper: Format Permission Name =====
function formatPermissionName(perm) {
    // Convert snake_case to Title Case with spaces
    return perm
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')
        .replace(/Perms?/i, '') // Remove "Perm" suffix
        .trim();
}

// ===== Helper: Create Individual Permission Item =====
function createPermissionItem(perm, username, userInfo) {
    const isAdmin = userInfo.is_admin;
    const isAllowed = !!userInfo.permissions[perm];
    
    const permItem = document.createElement('div');
    permItem.classList.add('permission-item');
    
    if (isAdmin) {
        permItem.classList.add('admin-disabled');
    }
    
    if (isAllowed) {
        permItem.classList.add('active');
    }
    
    const icon = PERMISSION_ICONS[perm] || '🔑';
    
    permItem.innerHTML = `
        <div class="permission-icon">${icon}</div>
        <div class="permission-label">${formatPermissionName(perm)}</div>
        <label class="permission-toggle">
            <input type="checkbox" ${isAllowed ? 'checked' : ''} ${isAdmin ? 'disabled' : ''}>
            <span class="toggle-slider"></span>
        </label>
        <div class="permission-tooltip">${perm}</div>
    `;
    
    // Add click handler to the entire item (not just checkbox)
    if (!isAdmin) {
        permItem.addEventListener('click', (e) => {
            // Don't trigger if clicking the toggle slider
            if (e.target.closest('.permission-toggle')) return;
            
            const checkbox = permItem.querySelector('input[type="checkbox"]');
            checkbox.checked = !checkbox.checked;
            checkbox.dispatchEvent(new Event('change'));
        });
    }
    
    // Add change handler for the checkbox
    const checkbox = permItem.querySelector('input[type="checkbox"]');
    checkbox.addEventListener('change', async () => {
        if (isAdmin) return;
        
        const newVal = checkbox.checked;
        const url = `/api/knowledge/perm/set/${encodeURIComponent(username)}/${encodeURIComponent(perm)}/${newVal}`;
        
        // Visual feedback
        permItem.classList.toggle('active', newVal);
        
        try {
            const res = await fetch(url, { method: 'GET' });
            const data = await res.json();
            
            if (!res.ok) {
                showToast(data.error || 'Failed to update permission', 'error');
                checkbox.checked = !newVal;
                permItem.classList.toggle('active', !newVal);
                return;
            }

            // Update local state
            currentUsers[username].permissions[perm] = newVal;
            
            // Update permissions stats
            const stats = permItem.closest('.permissions').querySelector('.permissions-stats');
            if (stats) {
                const activePerms = Object.values(currentUsers[username].permissions).filter(v => v).length;
                stats.textContent = `${activePerms}/${validPermissions.length}`;
            }
            
            showToast(`"${formatPermissionName(perm)}" ${newVal ? 'granted' : 'revoked'}`, 'success');
        } catch (err) {
            console.error('Error updating permission:', err);
            checkbox.checked = !newVal;
            permItem.classList.toggle('active', !newVal);
            showToast('Failed to update permission', 'error');
        }
    });
    
    return permItem;
}

function createUserCard(username, info) {
    const card = document.createElement('div');
    card.classList.add('user-card');

    // Header with user info
    const header = document.createElement('div');
    header.classList.add('user-header');
    header.innerHTML = `
        <div>
            <h2>${username}${info.is_admin ? ' 👑' : ''}</h2>
            <span class="status ${info.arrested ? 'arrested' : 'free'}">
                ${info.arrested ? '🔒 Arrested' : '🔓 Active'}
            </span>
        </div>
        <div class="user-meta">
            <span class="meta-item">${info.is_admin ? 'Admin' : 'User'}</span>
            <span class="meta-item">${Object.keys(info.permissions).filter(p => info.permissions[p]).length} perms</span>
        </div>
    `;
    card.appendChild(header);

    // Action buttons
    const actions = document.createElement('div');
    actions.classList.add('actions');

    const arrestBtn = document.createElement('button');
    arrestBtn.textContent = info.arrested ? 'Release' : 'Arrest';
    arrestBtn.className = info.arrested ? 'btn release' : 'btn arrest';
    arrestBtn.title = info.arrested ? 'Restore user access' : 'Block user from system';
    actions.appendChild(arrestBtn);

    arrestBtn.addEventListener('click', async () => {
        const action = info.arrested ? 'release' : 'arrest';
        const confirmText = info.arrested 
            ? `Release ${username}?` 
            : `Arrest ${username}? This will prevent them from accessing the system.`;
        
        if (!confirm(confirmText)) return;

        const endpoint = info.arrested ? 'release' : 'arrest';
        const url = `/api/knowledge/${endpoint}/${encodeURIComponent(username)}`;

        try {
            const res = await fetch(url, { method: 'GET' });
            const data = await res.json();
            
            if (!res.ok) {
                showToast(data.error || `Failed to ${action} user`, 'error');
                return;
            }

            // Update local state
            info.arrested = !info.arrested;
            currentUsers[username] = info;

            // Update UI
            arrestBtn.textContent = info.arrested ? 'Release' : 'Arrest';
            arrestBtn.className = info.arrested ? 'btn release' : 'btn arrest';
            header.querySelector('.status').textContent = info.arrested ? '🛑 Arrested' : '✅ Free';
            header.querySelector('.status').className = `status ${info.arrested ? 'arrested' : 'free'}`;
            
            showToast(data.message || `User ${action}ed successfully`, 'success');
        } catch (err) {
            console.error(`Error ${action}ing user:`, err);
            showToast(`Failed to ${action} user`, 'error');
        }
    });

    card.appendChild(actions);

    // Permissions section - NEW DESIGN
    const permContainer = document.createElement('div');
    permContainer.classList.add('permissions');
    
    // Permissions header
    const permHeader = document.createElement('div');
    permHeader.classList.add('permissions-header');
    permHeader.innerHTML = `
        <h3>Permissions</h3>
        <span class="permissions-stats">
            ${Object.keys(info.permissions).filter(p => info.permissions[p]).length}/${validPermissions.length}
        </span>
    `;
    permContainer.appendChild(permHeader);

    // Group permissions by category
    const groupedPermissions = groupPermissionsByCategory();
    
    // Create category sections
    Object.entries(groupedPermissions).forEach(([category, perms]) => {
        // Only show categories that have permissions for this user
        const userPermsInCategory = perms.filter(perm => validPermissions.includes(perm));
        if (userPermsInCategory.length === 0) return;
        
        const categorySection = document.createElement('div');
        categorySection.classList.add('permission-category');
        
        const categoryHeader = document.createElement('div');
        categoryHeader.classList.add('category-header');
        categoryHeader.innerHTML = `
            <span class="category-icon">📁</span>
            <span class="category-title">${category}</span>
        `;
        categorySection.appendChild(categoryHeader);
        
        const permGrid = document.createElement('div');
        permGrid.classList.add('permissions-grid');
        
        userPermsInCategory.forEach(perm => {
            const permItem = createPermissionItem(perm, username, info);
            permGrid.appendChild(permItem);
        });
        
        categorySection.appendChild(permGrid);
        permContainer.appendChild(categorySection);
    });

    card.appendChild(permContainer);
    return card;
}

function renderGroupedPermissions(username, info) {
  const permArea = document.getElementById('permArea');
  permArea.innerHTML = '';

  const grouped = groupPermissionsByCategory();

  Object.entries(grouped).forEach(([category, perms]) => {
    const validInCategory = perms.filter(p => validPermissions.includes(p));
    if (validInCategory.length === 0) return;

    const categoryDiv = document.createElement('div');
    categoryDiv.className = 'permission-category';

    const header = document.createElement('div');
    header.className = 'category-header';
    header.innerHTML = `
      <span class="category-icon">📁</span>
      <span>${category}</span>
    `;
    categoryDiv.appendChild(header);

    const grid = document.createElement('div');
    grid.className = 'permissions-grid';

    validInCategory.forEach(perm => {
      grid.appendChild(createPermissionItem(perm, username, info));
    });

    categoryDiv.appendChild(grid);
    permArea.appendChild(categoryDiv);
  });
}

function wireArrestButton(username, info) {
  const btn = document.getElementById('toggleArrestBtn');

  btn.addEventListener('click', async () => {
    const action = info.arrested ? 'release' : 'arrest';
    const confirmText = info.arrested
      ? `Release ${username}?`
      : `Arrest ${username}? This will block system access.`;

    if (!confirm(confirmText)) return;

    try {
      const res = await fetch(
        `/api/knowledge/${action}/${encodeURIComponent(username)}`,
        { method: 'GET' }
      );

      const data = await res.json();
      if (!res.ok) {
        showToast(data.error || 'Action failed', 'error');
        return;
      }

      // Update local state
      info.arrested = !info.arrested;
      currentUsers[username] = info;

      showToast(data.message || 'User updated', 'success');

      // Refresh detail + sidebar
      showUserDetail(username);
      refreshUserListItem(username);

    } catch (err) {
      console.error(err);
      showToast('Failed to update user', 'error');
    }
  });
}

function showUserDetail(username) {
  const container = document.getElementById('userDetail');
  const info = currentUsers[username];

  container.innerHTML = `
    <h2>${username}${info.is_admin ? ' 👑' : ''}</h2>

    <div class="user-detail-grid">
      <!-- META COLUMN -->
      <div class="detail-column">
        <h3>User Info</h3>
        <p><strong>Role:</strong> ${info.is_admin ? 'Admin' : 'User'}</p>
        <p><strong>Status:</strong> 
          <span class="status ${info.arrested ? 'arrested' : 'free'}">
            ${info.arrested ? 'Arrested' : 'Active'}
          </span>
        </p>

        <button id="toggleArrestBtn"
          class="btn ${info.arrested ? 'release' : 'arrest'}">
          ${info.arrested ? 'Release' : 'Arrest'}
        </button>
      </div>

      <!-- PERMISSIONS COLUMN -->
      <div class="detail-column">
        <h3>Permissions</h3>
        <div id="permArea" class="permissions"></div>
      </div>

      <!-- STATS COLUMN -->
      <div class="detail-column">
        <h3>Stats</h3>
        <p>
          ${
            Object.values(info.permissions).filter(v => v).length
          } / ${validPermissions.length} enabled
        </p>
      </div>
    </div>
  `;

  renderGroupedPermissions(username, info);
  wireArrestButton(username, info);
}

function createUserListItem(username) {
  const info = currentUsers[username];
  const item = document.createElement('div');
  item.className = 'user-list-item';

  item.innerHTML = `
    <span>${username}${info.is_admin ? ' 👑' : ''}</span>
    <span class="status ${info.arrested ? 'arrested' : 'free'}"></span>
  `;

  item.addEventListener('click', () => {
    document.querySelectorAll('.user-list-item')
      .forEach(i => i.classList.remove('active'));
    item.classList.add('active');
    showUserDetail(username);
  });

  return item;
}

async function loadUsers() {
  const list = document.getElementById('userList');
  list.innerHTML = '<div class="loading">Loading...</div>';

  try {
    const data = await fetchUserData();
    validPermissions = data.valid_permissions || [];
    currentUsers = data.users || {};

    list.innerHTML = '';

    Object.keys(currentUsers)
      .sort()
      .forEach(username => {
        list.appendChild(createUserListItem(username));
      });

  } catch {
    list.innerHTML = '<div class="error">Failed to load users</div>';
  }
}

// ===== Settings Management Functions =====
async function loadSettings() {
    try {
        const res = await fetch('/api/knowledge/settings/load');
        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            throw new Error(data.error || `HTTP ${res.status}`);
        }
        
        const data = await res.json();
        
        // Weekday mapping
        const weekdaysMap = {
            1: "monday",
            2: "tuesday",
            3: "wednesday",
            4: "thursday",
            5: "friday",
            6: "saturday",
            7: "sunday"
        };
        
        // Convert weekday_end from number to text if needed
        if (data.weekday_end !== undefined && typeof data.weekday_end === 'number') {
            data.weekday_end = weekdaysMap[data.weekday_end];
        }

        // Update all config inputs
        const inputs = document.querySelectorAll('.config-card input, .config-card select');
        inputs.forEach(input => {
            const name = input.dataset.configName;
            if (!name || !(name in data)) return;
            
            let value = data[name];
            
            if (input.type === 'checkbox') {
                input.checked = Boolean(value);
            } else if (input.type === 'select-one') {
                input.value = String(value).toLowerCase();
            } else {
                input.value = value;
            }
        });
        
        showToast('Settings loaded successfully', 'success');
    } catch (err) {
        console.error('Error loading settings:', err);
        showToast(`Failed to load settings: ${err.message}`, 'error');
    }
}

async function saveSettings() {
    if (!confirm('Are you sure you want to save all settings? This will overwrite existing configuration.')) {
        return;
    }

    const config = {};
    const inputs = document.querySelectorAll('.config-card input, .config-card select');
    
    inputs.forEach(input => {
        const name = input.dataset.configName;
        if (!name) return;
        
        let value;
        if (input.type === 'checkbox') {
            value = input.checked;
        } else if (input.type === 'number') {
            value = Number(input.value);
        } else {
            value = input.value;
        }
        
        config[name] = value;
    });

    try {
        const res = await fetch('/api/knowledge/settings/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config })
        });
        
        const data = await res.json();
        
        if (!res.ok) {
            showToast(data.error || 'Failed to save settings', 'error');
            return;
        }
        
        showToast(data.message || 'Settings saved successfully!', 'success');
    } catch (err) {
        console.error('Error saving settings:', err);
        showToast('Failed to save settings', 'error');
    }
}

// ===== Toast System =====
function showToast(message, type = 'error') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast show ${type}`;
    
    setTimeout(() => {
        toast.className = 'toast';
    }, 4000);
}

// ===== Theme Management =====
function initTheme() {
    const themeBtn = document.getElementById('themeToggle');
    const prefersLight = window.matchMedia('(prefers-color-scheme: light)');
    
    // Set initial theme from localStorage or system preference
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
    } else if (prefersLight.matches) {
        document.documentElement.setAttribute('data-theme', 'light');
    }
    
    updateThemeButton();
    
    // Theme toggle click handler
    themeBtn.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateThemeButton();
    });
    
    // Listen for system theme changes
    prefersLight.addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
            const newTheme = e.matches ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            updateThemeButton();
        }
    });
}

function updateThemeButton() {
    const themeBtn = document.getElementById('themeToggle');
    const currentTheme = document.documentElement.getAttribute('data-theme');
    
    if (currentTheme === 'light') {
        themeBtn.textContent = '🌙 Dark Mode';
    } else {
        themeBtn.textContent = '☀️ Light Mode';
    }
}

// ===== Initialization =====
document.addEventListener('DOMContentLoaded', () => {
    // Initialize theme
    initTheme();
    
    // Restore last tab if still valid
    const savedTab = localStorage.getItem(TAB_MEMORY_KEY);
    const savedTime = Number(localStorage.getItem(TAB_MEMORY_TIME_KEY));
    const now = Date.now();

    if (savedTab && savedTime && (now - savedTime) < TAB_MEMORY_DURATION) {
        switchTab(savedTab);
    } else {
        // Expired or none → default
        switchTab('auth');
        localStorage.removeItem(TAB_MEMORY_KEY);
        localStorage.removeItem(TAB_MEMORY_TIME_KEY);
    }
    
    // Set up tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            switchTab(btn.dataset.tab);
        });
    });
    
    // Back button
    document.getElementById('backBtn').addEventListener('click', () => {
        window.location.href = '/apps';
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl+1 for auth tab, Ctrl+2 for settings tab
        if (e.ctrlKey) {
            if (e.key === '1') {
                e.preventDefault();
                switchTab('auth');
            } else if (e.key === '2') {
                e.preventDefault();
                switchTab('settings');
            }
        }
        
        // F5 to refresh current tab
        if (e.key === 'F5') {
            e.preventDefault();
            if (currentTab === 'auth') {
                loadUsers();
            } else {
                loadSettings();
            }
        }
    });
});