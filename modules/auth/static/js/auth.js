async function fetchUserList() {
    const response = await fetch('/api/auth/userlist');
    if (!response.ok) throw new Error(`Server error: ${response.status}`);
    return response.json();
}

async function toggleArrest(username, isArrested, button, statusDiv) {
    const action = isArrested ? 'release' : 'arrest';
    if (!confirm(`Are you sure you want to ${action} ${username}?`)) return;

    const url = isArrested 
        ? `/api/auth/release/${encodeURIComponent(username)}`
        : `/api/auth/arrest/${encodeURIComponent(username)}`;

    try {
        const response = await fetch(url, { method: 'GET' });
        if (!response.ok) throw new Error(`Server error: ${response.status}`);

        // Update UI
        statusDiv.textContent = 'Arrested: ' + (isArrested ? 'No' : 'Yes');
        if (isArrested) {
            statusDiv.classList.remove('arrested');
            button.textContent = 'Arrest';
            button.classList.remove('release');
            button.classList.add('arrest');
        } else {
            statusDiv.classList.add('arrested');
            button.textContent = 'Release';
            button.classList.remove('arrest');
            button.classList.add('release');
        }

    } catch (err) {
        console.error('Error toggling arrest:', err);
        alert('Failed to update arrest status.');
    }
}

async function loadUserPermissions() {
    try {
        const data = await fetchUserList();
        const { valid_permissions, users } = data;

        const container = document.getElementById('cardsContainer');
        container.innerHTML = ''; // clear any existing cards

        Object.entries(users).forEach(([username, info]) => {
            const card = document.createElement('div');
            card.classList.add('user-card');

            // Username
            const name = document.createElement('h2');
            name.textContent = username;
            card.appendChild(name);

            // Arrested status
            const arrestedDiv = document.createElement('div');
            arrestedDiv.textContent = 'Arrested: ' + (info.arrested ? 'Yes' : 'No');
            if (info.arrested) arrestedDiv.classList.add('arrested');
            card.appendChild(arrestedDiv);

            // Arrest / Release button
            const btn = document.createElement('button');
            btn.classList.add('arrest-btn');
            btn.style.marginTop = '10px';

            const updateButton = (arrested) => {
                if (arrested) {
                    btn.textContent = 'Release';
                    btn.classList.remove('arrest');
                    btn.classList.add('release');
                } else {
                    btn.textContent = 'Arrest';
                    btn.classList.remove('release');
                    btn.classList.add('arrest');
                }
            };

            updateButton(info.arrested);

            btn.addEventListener('click', () => {
                toggleArrest(username, info.arrested, btn, arrestedDiv);
                info.arrested = !info.arrested; // update after confirmation
                updateButton(info.arrested);
            });

            card.appendChild(btn);

            // Permissions
            const permsContainer = document.createElement('div');
            permsContainer.classList.add('permissions');

            valid_permissions.forEach(perm => {
                const permDiv = document.createElement('div');
                permDiv.classList.add('permission');

                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.checked = !!info.permissions[perm];
                checkbox.id = `perm-${username}-${perm}`;

                const label = document.createElement('label');
                label.textContent = perm;
                label.setAttribute('for', checkbox.id);

                // Toggle permission via GET when checkbox or label is clicked
                const togglePermission = async () => {
                    const newVal = checkbox.checked ? 1 : 0;
                    const url = `/api/auth/perm/set/${encodeURIComponent(username)}/${encodeURIComponent(perm)}/${newVal}`;
                    try {
                        const res = await fetch(url, { method: 'GET' });
                        if (!res.ok) throw new Error(`Server error: ${res.status}`);
                    } catch (err) {
                        console.error('Failed to update permission:', err);
                        checkbox.checked = !checkbox.checked; // revert
                        alert('Failed to update permission.');
                    }
                };

                checkbox.addEventListener('change', togglePermission);
                label.addEventListener('click', (e) => {
                    e.preventDefault(); // prevent double toggling
                    checkbox.checked = !checkbox.checked;
                    togglePermission();
                });

                permDiv.appendChild(checkbox);
                permDiv.appendChild(label);
                permsContainer.appendChild(permDiv);
            });

            card.appendChild(permsContainer);
            container.appendChild(card);
        });

    } catch (err) {
        console.error('Error loading user permissions:', err);
    }
}

loadUserPermissions();
