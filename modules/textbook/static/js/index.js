// noinspection JSDeprecatedSymbols

// --- Exec Commands ---
function execCmd(command) {
    document.execCommand(command, false, null);
}

function execCmdWithArg(command, arg) {
    document.execCommand(command, false, arg);
}

// --- PDF Save ---
function saveAsPDF() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();

    const title = document.getElementById('pdf-title').value || 'Untitled Document';
    const content = document.getElementById('editor').innerText;

    doc.setFontSize(18);
    doc.text(title, 10, 20);

    doc.setFontSize(12);
    doc.text(content, 10, 30);

    doc.save(`${title}.pdf`);
}

// --- Server Save ---
let currentArchiveId = null;

function saveToServer() {
    const title = document.getElementById('pdf-title').value || 'Untitled Document';
    const content = document.getElementById('editor').innerHTML;
    let tags = document.getElementById('pdf-tags').value || '';

    if (tags.includes(' ')) {
        showToast('Tags should not contain spaces. Use commas to separate tags.', 'error');
        return;
    }

    tags = tags.split(',').map(tag => tag.trim()).filter(tag => tag);

    fetch('/api/archives/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ archive_id: currentArchiveId, title, content, tags })
    })
    .then(res => res.json())
    .then(data => {
        if (data.archive_id) currentArchiveId = data.archive_id;
        showToast('Document saved successfully!');
        loadArchiveList();
    })
    .catch(err => {
        console.error('Error:', err);
        showToast('An error occurred while saving.');
    });
}

// --- Archives ---
let allArchives = [];

function loadArchiveList() {
    fetch('/api/archives/get_all')
        .then(res => res.json())
        .then(data => {
            allArchives = Array.isArray(data.pdfs) ? data.pdfs : [];
            renderArchiveList(allArchives);
        })
        .catch(err => {
            console.error('Error fetching archive list:', err);
            document.getElementById('archive-list').innerHTML = '<li>Error loading archives</li>';
        });
}

function loadArchiveById(id) {
    fetch('/api/archives/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
    })
    .then(res => res.json())
    .then(data => {
        if (data.content && data.title !== undefined) {
            document.getElementById('editor').innerHTML = data.content;
            document.getElementById('pdf-title').value = data.title;
            document.getElementById('pdf-tags').value = data.tags?.join(',') || '';
            currentArchiveId = id;
        } else {
            showToast('Invalid archive format', 'error');
        }
    })
    .catch(err => {
        console.error('Failed to load archive:', err);
        showToast('Error loading archive.', 'error');
    });
}

function createNewDocument(alertUser = true) {
    document.getElementById('editor').innerHTML = '<p>Start editing your document...</p>';
    document.getElementById('pdf-title').value = '';
    document.getElementById('pdf-tags').value = '';
    currentArchiveId = null;
    setMode(true);
    if (alertUser) showToast('New document created. Start editing!');
}

function renderArchiveList(archives) {
    const list = document.getElementById('archive-list');
    list.innerHTML = '';

    if (archives.length === 0) {
        list.innerHTML = '<li>No matching archives found.</li>';
        return;
    }

    archives.forEach(doc => {
        const li = document.createElement('li');
        li.innerHTML = `
            <strong>${doc.title}</strong><br>
            <small>${doc.tags || 'No tags'} | ID: ${doc.id}</small>
        `;
        li.style.cursor = 'pointer';
        li.onclick = () => loadArchiveById(doc.id);
        list.appendChild(li);
    });
}

function filterArchives() {
    const query = document.getElementById('search-input').value.trim().toLowerCase();
    const parts = query.split(',').map(p => p.trim()).filter(Boolean);

    const filtered = allArchives.filter(doc => {
        const titleMatch = doc.title.toLowerCase().includes(query);
        const idMatch = String(doc.id).toLowerCase().includes(query);
        const tagsMatch = parts.every(part =>
            doc.tags?.some(tag => tag.toLowerCase().includes(part))
        );
        return titleMatch || idMatch || tagsMatch;
    });

    renderArchiveList(filtered);
}

// --- Mode Switching ---
const modeSwitchBar = document.getElementById('mode-switch-bar');
const editor = document.getElementById('editor');
const toolbar = document.querySelector('.toolbar');
const switchbarSaveBtn = document.getElementById('switchbar_save_btn');
let isEditMode = true;

function setMode(editMode) {
    editor.contentEditable = editMode ? "true" : "false";
    toolbar.style.display = editMode ? "flex" : "none";
    editor.style.backgroundColor = "#ffffff";

    if (switchbarSaveBtn) {
        switchbarSaveBtn.style.display = editMode ? "none" : "inline-block";
    }

    modeSwitchBar.textContent = editMode ? "Edit Mode" : "View Mode";
    modeSwitchBar.style.backgroundColor = editMode ? "#4CAF50" : "#2196F3";

    isEditMode = editMode;
    setCookie('pdf_editor_mode', editMode ? 'edit' : 'view');
}

// --- Cookies ---
function setCookie(name, value, days = 7) {
    const d = new Date();
    d.setTime(d.getTime() + days * 86400000);
    document.cookie = `${name}=${value};path=/;expires=${d.toUTCString()}`;
}

function getCookie(name) {
    return document.cookie
        .split(';')
        .map(c => c.trim().split('='))
        .find(([k]) => k === name)?.[1] || null;
}

// --- Toast Notifications ---
function showToast(message, type = 'success', duration = 3000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span>${message}</span>
        <button class="close-btn" onclick="this.parentElement.remove()">×</button>
    `;

    container.appendChild(toast);

    const autoRemove = setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(-10px)';
        setTimeout(() => toast.remove(), 300);
    }, duration);

    toast.querySelector('.close-btn').addEventListener('click', () => {
        clearTimeout(autoRemove);
    });
}

// --- Document Destroy ---
document.getElementById('destroy-btn').addEventListener('click', () => {
    if (!currentArchiveId) {
        showToast("This document hasn't been saved yet, nothing to destroy!", 'error');
        return;
    }

    const confirmed = confirm("⚠️ Are you sure you want to destroy this document? This cannot be undone!");
    if (!confirmed) return;

    fetch('/api/archives/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: currentArchiveId })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Document shredded", 'success');
            createNewDocument(false);
            loadArchiveList();
        } else {
            showToast("Failed to delete document", 'error');
        }
    })
    .catch(err => {
        console.error(err);
        showToast("Error deleting document", 'error');
    });
});

// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
    loadArchiveList();
    createNewDocument(false);

    const savedMode = getCookie('pdf_editor_mode');
    setMode(savedMode === 'edit');

    modeSwitchBar.addEventListener('click', () => {
        setMode(!isEditMode);
    });
});

// --- Keyboard Shortcuts ---
document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        saveToServer();
    }

    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        document.execCommand('undo');
    }
});
