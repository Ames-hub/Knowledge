let scheduleData = {};
let hasUnsavedChanges = false;

// Room filter functionality
document.addEventListener('DOMContentLoaded', function() {
    const roomFilter = document.getElementById('room-filter');
    const dateFilter = document.getElementById('date-filter');
    const saveBtn = document.getElementById('save-btn');
    const exportBtn = document.getElementById('export-btn');
    
    // Set today's date as default
    const today = new Date().toISOString().split('T')[0];
    dateFilter.value = today;

    // Load initial schedule data
    loadScheduleData(today);

    // Event listeners
    roomFilter.addEventListener('change', filterSchedule);
    dateFilter.addEventListener('change', function() {
    loadScheduleData(this.value);
    });
    saveBtn.addEventListener('click', saveScheduleData);
    exportBtn.addEventListener('click', exportSchedule);

    // Initialize editable fields
    initializeEditableFields();
});

async function loadScheduleData(date) {
    try {
    document.getElementById('schedule-body').innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 20px;">Loading schedule...</td></tr>';
    
    const response = await fetch(`/api/files/get/${FileCFID}/scheduling/fetch/${date}`);
    
    if (!response.ok) {
        throw new Error(`Failed to load schedule: ${response.statusText}`);
    }
    
    scheduleData = await response.json();
    renderScheduleTable();
    hasUnsavedChanges = false;
    updateSaveButton();
    
    } catch (error) {
    console.error('Error loading schedule:', error);
    showStatus(`Error loading schedule: ${error.message}`, 'error');
    document.getElementById('schedule-body').innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 20px; color: #dc3545;">Error loading schedule</td></tr>';
    }
}

function renderScheduleTable() {
    const scheduleBody = document.getElementById('schedule-body');
    const times = generateTimeSlots();
    
    let html = '';
    
    times.forEach(time => {
    const scheduleItem = scheduleData[time] || {
        time: time,
        activity: '',
        auditor: '',
        room: ''
    };
    
    const roomValue = scheduleItem.room.toLowerCase().replace(/[^a-z0-9]/g, '');
    
    html += `
        <tr data-time="${time}" data-room="${roomValue}">
        <td class="time-col">${time}</td>
        <td class="activity-col editable-field" data-field="activity">${scheduleItem.activity || '—'}</td>
        <td class="auditor-col editable-field" data-field="auditor">${scheduleItem.auditor || '—'}</td>
        <td class="room-col editable-field" data-field="room">${scheduleItem.room || '—'}</td>
        </tr>
    `;
    });
    
    scheduleBody.innerHTML = html;
    initializeEditableFields();
    filterSchedule(); // Apply current filter
}

function generateTimeSlots() {
    const times = [];
    for (let hour = 0; hour < 24; hour++) {
    const period = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour % 12 || 12;
    times.push(`${displayHour}:00 ${period}`);
    }
    return times;
}

function initializeEditableFields() {
    const editableFields = document.querySelectorAll('.editable-field');
    
    editableFields.forEach(field => {
    field.addEventListener('click', function() {
        const row = this.closest('tr');
        const time = row.getAttribute('data-time');
        const fieldType = this.getAttribute('data-field');
        const currentValue = this.textContent === '—' ? '' : this.textContent;
        
        this.innerHTML = `<input type="text" class="edit-input" value="${currentValue}" data-original="${currentValue}">`;
        const input = this.querySelector('.edit-input');
        
        input.focus();
        input.select();
        
        input.addEventListener('blur', function() {
        finishEditing(input, time, fieldType);
        });
        
        input.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            this.blur();
        }
        });
    });
    });
}

function finishEditing(input, time, fieldType) {
    const newValue = input.value.trim();
    const originalValue = input.getAttribute('data-original');
    const cell = input.closest('td');
    
    if (newValue !== originalValue) {
    // Update the data
    if (!scheduleData[time]) {
        scheduleData[time] = { time: time, activity: '', auditor: '', room: '' };
    }
    scheduleData[time][fieldType] = newValue;
    
    // Update display
    cell.textContent = newValue || '—';
    cell.classList.add('editable-field');
    
    // Mark as having unsaved changes
    hasUnsavedChanges = true;
    updateSaveButton();
    
    // Update room filter data attribute if room was changed
    if (fieldType === 'room') {
        const row = cell.closest('tr');
        const roomValue = newValue.toLowerCase().replace(/[^a-z0-9]/g, '');
        row.setAttribute('data-room', roomValue);
    }
    } else {
    // Restore original display
    cell.textContent = originalValue || '—';
    cell.classList.add('editable-field');
    }
}

function filterSchedule() {
    const selectedRoom = document.getElementById('room-filter').value;
    const scheduleRows = document.getElementById('schedule-body').getElementsByTagName('tr');
    
    for (let row of scheduleRows) {
    if (selectedRoom === 'all') {
        row.style.display = '';
    } else {
        if (row.getAttribute('data-room') === selectedRoom) {
        row.style.display = '';
        } else {
        row.style.display = 'none';
        }
    }
    }
}

function updateSaveButton() {
    const saveBtn = document.getElementById('save-btn');
    saveBtn.disabled = !hasUnsavedChanges;
}

async function saveScheduleData() {
    try {
    showStatus('Saving schedule...', 'info');
    
    const response = await fetch(`/api/files/get/${FileCFID}/scheduling/save`, {
        method: 'POST',
        headers: {
        'Content-Type': 'application/json',
        },
        body: JSON.stringify(scheduleData)
    });
    
    if (!response.ok) {
        throw new Error(`Failed to save schedule: ${response.statusText}`);
    }
    
    const result = await response.json();
    hasUnsavedChanges = false;
    updateSaveButton();
    showStatus('Schedule saved successfully', 'success');
    
    // Hide success message after 2 seconds
    setTimeout(() => {
        hideStatus();
    }, 2000);
    
    } catch (error) {
    console.error('Error saving schedule:', error);
    showStatus(`Error saving schedule: ${error.message}`, 'error');
    }
}

function exportSchedule() {
    // Simple export functionality - could be enhanced to download as CSV
    const date = document.getElementById('date-filter').value;
    const dataStr = JSON.stringify(scheduleData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `schedule-${FileCFID}-${date}.json`;
    link.click();
    URL.revokeObjectURL(url);
}

function showStatus(message, type) {
    const statusElement = document.getElementById('status-message');
    statusElement.textContent = message;
    statusElement.className = `status-message status-${type}`;
    statusElement.style.display = 'block';
}

function hideStatus() {
    const statusElement = document.getElementById('status-message');
    statusElement.style.display = 'none';
}