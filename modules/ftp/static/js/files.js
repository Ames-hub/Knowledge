// DOM references
const fileGrid = document.getElementById('file-grid');
const breadcrumbsEl = document.getElementById('breadcrumbs');
const contextMenu = document.getElementById('context-menu');
const searchInput = document.getElementById('search-input');
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');

let currentPath = []; // path array
let currentFolderData = { folders: [], files: [] };
let selectedItem = null;

// Format file size
function formatFileSize(size) {
  if (size < 1024) return size + ' B';
  else if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB';
  else if (size < 1024 * 1024 * 1024) return (size / 1024 / 1024).toFixed(1) + ' MB';
  else return (size / 1024 / 1024 / 1024).toFixed(1) + ' GB';
}

// Fetch folder contents from API using POST
async function fetchFolder(pathArr) {
  try {
    const res = await fetch(`/api/ftp/walk`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: '/' + pathArr.join('/') })
    });

    const data = await res.json();
    // Convert API response to Explorer format
    currentFolderData = {
      folders: data.folders.map(f => ({ ...f, type: 'folder', children: [] })),
      files: data.files.map(f => ({ ...f, type: 'file' }))
    };

    renderFiles(currentFolderData);
    updateBreadcrumbs();
  } catch (err) {
    console.error('Failed to fetch folder:', err);
  }
}

function renderFiles(data) {
  fileGrid.innerHTML = '';

  const combined = [...data.folders, ...data.files];

  combined.forEach(item => {
    const div = document.createElement('div');
    div.classList.add('file-item');
    if (item.type === 'folder') div.classList.add('folder');
    div.innerHTML = `
      <div class="file-icon">${item.type === 'folder' ? '📁' : '📄'}</div>
      <div class="filename">${item.name}</div>
      ${item.type === 'file' ? `<div class="file-size">${formatFileSize(item.size)}</div>` : ''}
    `;

    // double-click: folder → navigate, file → download
    div.addEventListener('dblclick', () => {
      if (item.type === 'folder') {
        currentPath.push(item.name);
        fetchFolder(currentPath);
      } else if (item.type === 'file') {
        const filePath = '/' + currentPath.concat(item.name).join('/');
        window.location.href = `/api/ftp/download?path=${encodeURIComponent(filePath)}`;
      }
    });

    // Right-click context menu for individual files/folders
    div.addEventListener('contextmenu', e => {
      e.preventDefault();
      selectedItem = item;

      // Build menu dynamically
      let menuHTML = '';
      if (item.type === 'file' && item.name.match(/\.(txt|json|js|md)$/i)) {
        menuHTML += '<div id="edit">Edit</div>';
      }
      menuHTML += '<div id="rename">Rename</div>';
      menuHTML += '<div id="delete">Delete</div>';

      contextMenu.innerHTML = menuHTML;
      contextMenu.style.top = e.pageY + 'px';
      contextMenu.style.left = e.pageX + 'px';
      contextMenu.style.display = 'block';

      // Edit
      const editBtn = document.getElementById('edit');
      if (editBtn) {
        editBtn.addEventListener('click', async () => {
          contextMenu.style.display = 'none';
          const filePath = '/' + currentPath.concat(item.name).join('/');
          const res = await fetch('/api/ftp/read-file', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: filePath })
          });
          const data = await res.json();
          if (!data.success) return alert('Failed to read file: ' + data.error);

          // Create overlay
          const overlay = document.createElement('div');
          overlay.classList.add('editor-overlay');
          overlay.innerHTML = `
            <div class="editor-modal">
              <h3>Editing: ${item.name}</h3>
              <textarea id="editor-textarea" style="width:100%; height:300px;">${data.content}</textarea>
              <div class="editor-buttons">
                <button id="editor-save">Save</button>
                <button id="editor-cancel">Cancel</button>
              </div>
            </div>
          `;
          document.body.appendChild(overlay);

          // Stop clicks inside modal from closing it
          overlay.querySelector('.editor-modal').addEventListener('click', e => e.stopPropagation());

          // Cancel button
          document.getElementById('editor-cancel').addEventListener('click', () => overlay.remove());

          // Save button
          document.getElementById('editor-save').addEventListener('click', async () => {
            const content = document.getElementById('editor-textarea').value;
            const saveRes = await fetch('/api/ftp/save', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ path: filePath, content })
            });
            const saveData = await saveRes.json();
            if (!saveData.success) return alert('Save failed: ' + saveData.error);

            overlay.remove();
            fetchFolder(currentPath);
          });
        });
      }

      // Rename
      document.getElementById('rename').addEventListener('click', async () => {
        contextMenu.style.display = 'none';
        const newName = prompt('Enter new name:', item.name);
        if (!newName || newName === item.name) return;

        const filePath = '/' + currentPath.concat(item.name).join('/');
        const res = await fetch('/api/ftp/rename', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: filePath, new_name: newName })
        });
        const data = await res.json();
        if (!data.success) return alert('Rename failed: ' + data.error);

        // Update local state
        if (item.type === 'folder') {
          const folder = currentFolderData.folders.find(f => f.name === item.name);
          if (folder) folder.name = newName;
        } else {
          const file = currentFolderData.files.find(f => f.name === item.name);
          if (file) file.name = newName;
        }
        renderFiles(currentFolderData);
      });

      // Delete
      document.getElementById('delete').addEventListener('click', async () => {
        contextMenu.style.display = 'none';
        const filePath = '/' + currentPath.concat(item.name).join('/');
        const res = await fetch('/api/ftp/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: filePath })
        });
        const data = await res.json();
        if (!data.success) return alert('Delete failed: ' + data.error);

        if (item.type === 'folder') {
          currentFolderData.folders = currentFolderData.folders.filter(f => f.name !== item.name);
        } else {
          currentFolderData.files = currentFolderData.files.filter(f => f.name !== item.name);
        }
        renderFiles(currentFolderData);
      });
    });

    fileGrid.appendChild(div);
  });

  applySearch();
}

function updateBreadcrumbs() {
  breadcrumbsEl.innerHTML = '';
  const rootSpan = document.createElement('span');
  rootSpan.textContent = 'Home';
  rootSpan.addEventListener('click', () => {
    currentPath = [];
    fetchFolder(currentPath);
  });
  breadcrumbsEl.appendChild(rootSpan);

  currentPath.forEach((name, idx) => {
    const span = document.createElement('span');
    span.textContent = name;
    span.addEventListener('click', () => {
      currentPath = currentPath.slice(0, idx + 1);
      fetchFolder(currentPath);
    });
    breadcrumbsEl.appendChild(span);
  });
}

// Search filter
function applySearch() {
  const term = searchInput.value.toLowerCase();
  Array.from(fileGrid.children).forEach(div => {
    const name = div.querySelector('.filename').textContent.toLowerCase();
    div.style.display = name.includes(term) ? '' : 'none';
  });
}
searchInput.addEventListener('input', applySearch);

// Right-click on empty grid for creating new folders/files
fileGrid.addEventListener('contextmenu', e => {
  if (!e.target.closest('.file-item')) {
    e.preventDefault();
    selectedItem = null;
    contextMenu.innerHTML = `
      <div id="create-folder">Create Folder</div>
      <div id="create-file">Create File</div>
    `;
    contextMenu.style.top = e.pageY + 'px';
    contextMenu.style.left = e.pageX + 'px';
    contextMenu.style.display = 'block';

    document.getElementById('create-folder').addEventListener('click', async () => {
      const folderName = prompt('Enter folder name:');
      if (!folderName) return contextMenu.style.display = 'none';
      try {
        const path = '/' + currentPath.join('/');
        const res = await fetch('/api/ftp/create-folder', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path, name: folderName })
        });
        const data = await res.json();
        if (!data.success) return alert('Create folder failed: ' + data.error);
        fetchFolder(currentPath);
      } catch (err) {
        console.error('Create folder failed', err);
        alert('Create folder failed due to network error');
      } finally {
        contextMenu.style.display = 'none';
      }
    });

    document.getElementById('create-file').addEventListener('click', async () => {
      const fileName = prompt('Enter file name:');
      if (!fileName) return contextMenu.style.display = 'none';
      try {
        const path = '/' + currentPath.join('/');
        const res = await fetch('/api/ftp/create-file', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path, name: fileName })
        });
        const data = await res.json();
        if (!data.success) return alert('Create file failed: ' + data.error);
        fetchFolder(currentPath);
      } catch (err) {
        console.error('Create file failed', err);
        alert('Create file failed due to network error');
      } finally {
        contextMenu.style.display = 'none';
      }
    });
  }
});

// Hide context menu on click elsewhere
document.addEventListener('click', () => {
  contextMenu.style.display = 'none';
});

// ==================== Drag & Drop uploads ====================
// Recursively read folder entries
function traverseFileTree(item, path, files) {
  return new Promise(resolve => {
    if (item.isFile) {
      item.file(file => {
        file.fullPath = path + file.name;
        files.push(file);
        resolve();
      });
    } else if (item.isDirectory) {
      const dirReader = item.createReader();
      dirReader.readEntries(entries => {
        const promises = [];
        for (const entry of entries) {
          promises.push(traverseFileTree(entry, path + item.name + "/", files));
        }
        Promise.all(promises).then(resolve);
      });
    }
  });
}

dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('dragover');
});
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  const items = e.dataTransfer.items;
  if (items) {
    const files = [];
    for (let i = 0; i < items.length; i++) {
      const entry = items[i].webkitGetAsEntry();
      if (entry) {
        traverseFileTree(entry, "", files).then(() => {
          uploadFiles(files);
        });
      }
    }
  } else {
    uploadFiles(e.dataTransfer.files);
  }
});
fileInput.addEventListener('change', e => {
  uploadFiles(e.target.files);
});

function arrayBufferToBase64(buffer) {
  const chunkSize = 0x8000; // 32 KB
  let binary = '';
  const bytes = new Uint8Array(buffer);
  for (let i = 0; i < bytes.length; i += chunkSize) {
    const chunk = bytes.subarray(i, i + chunkSize);
    binary += String.fromCharCode.apply(null, chunk);
  }
  return btoa(binary);
}

async function uploadFiles(files) {
  const payload = {
    path: "/" + currentPath.join("/"),
    files: []
  };

  for (const file of files) {
    if (file.type === "") {
      // This might be a directory placeholder, skip
      continue;
    }
    const arrayBuffer = await file.arrayBuffer();
    const base64 = arrayBufferToBase64(arrayBuffer);

    // Keep relative paths for folder uploads
    const relativePath = file.webkitRelativePath || file.name;

    payload.files.push({ name: relativePath, data: base64 });
  }

  try {
    const res = await fetch("/api/ftp/upload", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) fetchFolder(currentPath);
    else alert("Upload failed: " + data.error);
  } catch (err) {
    console.error("Upload failed", err);
    alert("Upload failed due to network error");
  }
}

// ==================== Delete ====================
document.getElementById('delete').addEventListener('click', async () => {
  if (!selectedItem) return;

  const filePath = '/' + currentPath.concat(selectedItem.name).join('/');
  try {
    const res = await fetch("/api/ftp/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: filePath })
    });
    const data = await res.json();
    if (!data.success) {
      alert("Delete failed: " + data.error);
      return;
    }

    // Update local state and re-render
    if (selectedItem.type === 'folder') {
      currentFolderData.folders = currentFolderData.folders.filter(f => f.name !== selectedItem.name);
    } else {
      currentFolderData.files = currentFolderData.files.filter(f => f.name !== selectedItem.name);
    }
    renderFiles(currentFolderData);
  } catch (err) {
    console.error("Delete failed", err);
    alert("Delete failed due to network error");
  } finally {
    contextMenu.style.display = 'none';
    selectedItem = null;
  }
});

// ==================== Rename ====================
document.getElementById('rename').addEventListener('click', async () => {
  if (!selectedItem) return;

  const newName = prompt('Enter new name:', selectedItem.name);
  if (!newName || newName === selectedItem.name) {
    contextMenu.style.display = 'none';
    return;
  }

  const filePath = '/' + currentPath.concat(selectedItem.name).join('/');
  try {
    const res = await fetch("/api/ftp/rename", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: filePath, new_name: newName })
    });
    const data = await res.json();
    if (!data.success) {
      alert("Rename failed: " + data.error);
      return;
    }

    // Update local state and re-render
    if (selectedItem.type === 'folder') {
      const folder = currentFolderData.folders.find(f => f.name === selectedItem.name);
      if (folder) folder.name = newName;
    } else {
      const file = currentFolderData.files.find(f => f.name === selectedItem.name);
      if (file) file.name = newName;
    }
    renderFiles(currentFolderData);
  } catch (err) {
    console.error("Rename failed", err);
    alert("Rename failed due to network error");
  } finally {
    contextMenu.style.display = 'none';
    selectedItem = null;
  }
});

// ==================== Hide context menu on click elsewhere ====================
document.addEventListener('click', () => {
  contextMenu.style.display = 'none';
});

// ==================== Initial fetch ====================
fetchFolder(currentPath);
