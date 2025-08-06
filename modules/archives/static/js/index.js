// noinspection JSDeprecatedSymbols

function execCmd(command) {
    document.execCommand(command, false, null);
}

function execCmdWithArg(command, arg) {
    document.execCommand(command, false, arg);
}

let currentArchiveId = null; // null means new document

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
        body: JSON.stringify({
            archive_id: currentArchiveId,
            title: title,
            content: content,
            tags: tags
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.archive_id) {
            currentArchiveId = data.archive_id; // <-- update currentArchiveId
        }
        showToast('Document saved successfully!');
        loadArchiveList();
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('An error occurred while saving.');
    });
}

let allArchives = []; // Store all fetched archives for filtering

function loadArchiveList() {
    fetch('/api/archives/get_all')
        .then(response => response.json())
        .then(data => {
            if (Array.isArray(data.pdfs)) {
                allArchives = data.pdfs;
                renderArchiveList(allArchives);
            } else {
                document.getElementById('archive-list').innerHTML = '<li>No archives found.</li>';
            }
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
        body: JSON.stringify({ id: id })
    })
    .then(response => response.json())
    .then(data => {
        const editor = document.getElementById('editor');
        const titleInput = document.getElementById('pdf-title');
        const tagsInput = document.getElementById('pdf-tags');

        if (data.content && data.title !== undefined) {
            editor.innerHTML = data.content;
            titleInput.value = data.title;
            tagsInput.value = data.tags ? data.tags.join(',') : '';
            currentArchiveId = id; // <-- save current archive ID
        } else {
            showToast('Invalid archive format', 'error');
        }
    })
    .catch(error => {
        console.error('Failed to load archive:', error);
        showToast('Error loading archive.', 'error');
    });
}

const modeSwitchBar = document.getElementById('mode-switch-bar');
const editor = document.getElementById('editor');
const toolbar = document.querySelector('.toolbar');
const switchbarSaveBtn = document.getElementById('switchbar_save_btn');
let isEditMode = true;

function updateMode() {
    if (isEditMode) {
        editor.contentEditable = "true";
        toolbar.style.display = "flex";
        editor.style.backgroundColor = "#ffffff";
        if (switchbarSaveBtn) switchbarSaveBtn.style.display = "none";
        modeSwitchBar.textContent = "Edit Mode";
        modeSwitchBar.style.backgroundColor = "#4CAF50";
        setCookie('pdf_editor_mode', 'edit');
    } else {
        editor.contentEditable = "false";
        toolbar.style.display = "none";
        editor.style.backgroundColor = "#ffffff";
        if (switchbarSaveBtn) switchbarSaveBtn.style.display = "inline-block";
        modeSwitchBar.textContent = "View Mode";
        modeSwitchBar.style.backgroundColor = "#999";
        setCookie('pdf_editor_mode', 'view');
    }
}

function setMode(editMode) {
    if (editMode) {
        editor.contentEditable = "true";
        toolbar.style.display = "flex";
        editor.style.backgroundColor = "#ffffff";
        if (switchbarSaveBtn) switchbarSaveBtn.style.display = "none";

        modeSwitchBar.style.backgroundColor = "#4CAF50";
        modeSwitchBar.textContent = "Edit Mode";
        setCookie('pdf_editor_mode', 'edit');
    } else {
        editor.contentEditable = "false";
        toolbar.style.display = "none";
        editor.style.backgroundColor = "#ffffff";
        if (switchbarSaveBtn) switchbarSaveBtn.style.display = "inline-block";

        modeSwitchBar.style.backgroundColor = "#2196F3";
        modeSwitchBar.textContent = "View Mode";
        setCookie('pdf_editor_mode', 'view');
    }
}

document.addEventListener('DOMContentLoaded', () => {
  // Restore mode from cookie or default to edit mode
  const savedMode = getCookie('pdf_editor_mode');
  let editMode = savedMode !== 'view';
  setMode(editMode);

  modeSwitchBar.addEventListener('click', () => {
    editMode = !editMode;
    setMode(editMode);
  });
});

function setCookie(name, value, days = 7) {
  const d = new Date();
  d.setTime(d.getTime() + days*24*60*60*1000);
  document.cookie = `${name}=${value};path=/;expires=${d.toUTCString()}`;
}

function getCookie(name) {
  const cookieArr = document.cookie.split(';');
  for (let c of cookieArr) {
    const [key, val] = c.trim().split('=');
    if (key === name) return val;
  }
  return null;
}

document.addEventListener('DOMContentLoaded', () => {
    loadArchiveList();
    createNewDocument(false); // Load new document on start
    
    const savedMode = getCookie('pdf_editor_mode');
    isEditMode = savedMode !== 'view';
    updateMode();

    modeSwitchBar.addEventListener('click', () => {
        isEditMode = !isEditMode;
        updateMode();
    });
});

document.addEventListener('keydown', function(e) {
    // CTRL+S => Save to server
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault(); // prevent browser save dialog
        saveToServer();
        return false;
    }

    // CTRL+Z => Undo
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        document.execCommand('undo'); // built-in undo
        return false;
    }
});

function createNewDocument(alert=true) {
    const editor = document.getElementById('editor');
    const titleInput = document.getElementById('pdf-title');
    const tagsInput = document.getElementById('pdf-tags');

    editor.innerHTML = '<p>Start editing your document...</p>';
    titleInput.value = '';
    tagsInput.value = '';

    currentArchiveId = null; // reset to null for a new document
    setMode(true);
    if (alert) {
        showToast('New document created. Start editing!');
    }
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
    
    // Split query into parts by comma for multi-tag search
    const searchParts = query.split(',').map(q => q.trim()).filter(q => q);

    const filtered = allArchives.filter(doc => {
        const titleMatch = doc.title.toLowerCase().includes(query);
        const idMatch = String(doc.id).toLowerCase().includes(query);
        
        // Check tags
        let tagsMatch = true;
        if (doc.tags && searchParts.length > 0) {
            // All search parts must match at least one tag
            tagsMatch = searchParts.every(part =>
                doc.tags.some(tag => tag.toLowerCase().includes(part))
            );
        }

        return titleMatch || idMatch || tagsMatch;
    });

    renderArchiveList(filtered);
}

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

    // Auto-remove after timeout
    const autoRemove = setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(-10px)';
        setTimeout(() => toast.remove(), 300);
    }, duration);

    // Cancel auto-remove if closed early
    toast.querySelector('.close-btn').addEventListener('click', () => {
        clearTimeout(autoRemove);
    });
}

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
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast("Document shredded", 'success');
            createNewDocument(false); // start fresh
            loadArchiveList(); // refresh the list
        } else {
            showToast("Failed to delete document", 'error');
        }
    })
    .catch(err => {
        console.error(err);
        showToast("Error deleting document", 'error');
    });
});
