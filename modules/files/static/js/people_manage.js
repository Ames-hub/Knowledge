// noinspection JSUnresolvedReference,ExceptionCaughtLocallyJS

const input = document.getElementById('name-input');
const list = document.getElementById('people-list');

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
            data.names.forEach((name, i) => {
                addNameToDOM(name, data.cfids[i]);
            });
        } else {
            console.warn('Unexpected data format:', data);
        }
    } catch (error) {
        console.error('Error fetching names:', error);
    }
}

function addNameToDOM(name, cfid) {
    const a = document.createElement('a');
    a.textContent = name;
    a.href = `/files/get/${cfid !== null ? cfid : name}`;
    list.appendChild(a);
}

async function addName() {
    const name = input.value.trim();
    if (!name) return;

    try {
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
            addNameToDOM(name, data.cfid);
            input.value = '';
        } else {
            alert('Server failed to create name');
        }
    } catch (error) {
        console.error('Error adding name:', error);
        alert('Error adding name');
    }
}

async function removeName() {
    const name = input.value.trim();
    if (!name) return;

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
            const items = list.getElementsByTagName('a');
            for (let i = 0; i < items.length; i++) {
                if (items[i].textContent === name) {
                    list.removeChild(items[i]);
                    break;
                }
            }
            input.value = '';
        } else {
            alert('Server failed to delete name');
        }
    } catch (error) {
        console.error('Error deleting name:', error);
        alert('Error deleting name');
    }
}

document.addEventListener('DOMContentLoaded', Get_Names);
