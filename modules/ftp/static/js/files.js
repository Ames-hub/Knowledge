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
        // trigger download request
        const filePath = '/' + currentPath.concat(item.name).join('/');
        window.location.href = `/api/ftp/download?path=${encodeURIComponent(filePath)}`;
      }
    });

    // right-click context menu
    div.addEventListener('contextmenu', e => {
      e.preventDefault();
      selectedItem = item;
      contextMenu.style.top = e.pageY + 'px';
      contextMenu.style.left = e.pageX + 'px';
      contextMenu.style.display = 'block';
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

// Context menu actions
document.getElementById('rename').addEventListener('click', () => {
  const newName = prompt('Enter new name:', selectedItem.name);
  if (newName) {
    selectedItem.name = newName;
    renderFiles(currentFolderData);
  }
  contextMenu.style.display = 'none';
});
document.getElementById('delete').addEventListener('click', () => {
  // In a real app you'd call DELETE API here
  if (selectedItem.type === 'folder') {
    currentFolderData.folders = currentFolderData.folders.filter(f => f.name !== selectedItem.name);
  } else {
    currentFolderData.files = currentFolderData.files.filter(f => f.name !== selectedItem.name);
  }
  renderFiles(currentFolderData);
  contextMenu.style.display = 'none';
});

// Hide context menu on click elsewhere
document.addEventListener('click', () => {
  contextMenu.style.display = 'none';
});

// Drag & Drop uploads
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
  uploadFiles(e.dataTransfer.files);
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
    const arrayBuffer = await file.arrayBuffer();
    const base64 = arrayBufferToBase64(arrayBuffer);
    payload.files.push({ name: file.name, data: base64 });
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

// Initial fetch
fetchFolder(currentPath);
