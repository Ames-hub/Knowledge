// ===== Global Variables & State =====
let currentTab = 'auth';
let currentUsers = {};
let validPermissions = [];

// ===== Permission Icons Mapping =====
const PERMISSION_ICONS = {
    // Auth/Admin permissions
    'auth_page': '👁️',
    'admin_panel': '🛡️',
    'app_settings': '⚙️',
    
    // General app permissions
    'view_pages': '📄',
    'edit_content': '✏️',
    'delete_content': '🗑️',
    
    // Module-specific permissions
    'battleplans_view': '📊',
    'battleplans_edit': '📝',
    'ledger_view': '💰',
    'ledger_edit': '💳',
    'knowledge_view': '📚',
    'knowledge_edit': '📖',
    
    // User management
    'user_manage': '👤',
    'user_delete': '❌',
    
    // System permissions
    'system_logs': '📋',
    'system_backup': '💾',
    'system_restore': '🔄'
};

// ===== Permission Categories =====
const PERMISSION_CATEGORIES = {
    'Administration': ['admin_panel', 'auth_page', 'app_settings'],
    'User Management': ['central_files'],
    'Content': ['bulletin_archives', 'ftp_server'],
    'Finances': ['ledger', 'invoicing', 'debt_tracking', 'financial_planning'],
    'production': ['battleplans', 'dianetics'],
    'System': ['app_logs', 'admin_panel']
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
    
    document.getElementById('headerSubtitle').textContent = 
        tabName === 'auth' ? 'Manage users, permissions, and arrest status' : 
        'Configure application settings and module behavior';
    
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

async function loadUsers() {
    const container = document.getElementById('userGrid');
    container.innerHTML = '<div class="loading">👥 Loading users...</div>';
    
    try {
        const data = await fetchUserData();
        validPermissions = data.valid_permissions || [];
        currentUsers = data.users || {};
        
        container.innerHTML = '';
        
        if (Object.keys(currentUsers).length === 0) {
            container.innerHTML = '<div class="loading">No users found</div>';
            return;
        }
        
        // Sort users: admins first, then alphabetical
        const sortedUsernames = Object.keys(currentUsers).sort((a, b) => {
            const aAdmin = currentUsers[a].is_admin;
            const bAdmin = currentUsers[b].is_admin;
            if (aAdmin && !bAdmin) return -1;
            if (!aAdmin && bAdmin) return 1;
            return a.localeCompare(b);
        });
        
        sortedUsernames.forEach(username => {
            container.appendChild(createUserCard(username, currentUsers[username]));
        });
        
        console.log(`Loaded ${sortedUsernames.length} users`, 'success');
    } catch (err) {
        container.innerHTML = '<div class="error">❌ Failed to load user data</div>';
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
    
    // Add view toggle button for permissions
    const viewToggle = document.createElement('button');
    viewToggle.id = 'viewToggle';
    viewToggle.className = 'nav-btn';
    viewToggle.textContent = '🔍 Compact View';
    viewToggle.style.marginLeft = '10px';
    
    viewToggle.addEventListener('click', () => {
        const cards = document.querySelectorAll('.user-card');
        const isCompact = cards[0]?.classList.contains('compact-view');
        
        cards.forEach(card => {
            card.classList.toggle('compact-view', !isCompact);
            card.querySelector('.permissions-grid')?.classList.toggle('compact-view', !isCompact);
        });
        
        viewToggle.textContent = isCompact ? '🔍 Compact View' : '🔍 Normal View';
    });
    
    // Insert after theme toggle
    const themeToggle = document.getElementById('themeToggle');
    themeToggle.parentNode.insertBefore(viewToggle, themeToggle.nextSibling);
    
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