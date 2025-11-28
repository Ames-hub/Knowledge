let weeklyScheduleData = {};   // All 7 days
let currentDayIndex = 0;       // 0 = Monday, 6 = Sunday
let hasUnsavedChanges = false;

// ---- DOM Initialization ----
document.addEventListener('DOMContentLoaded', () => {
    const roomFilter = document.getElementById('room-filter');
    const dayFilter = document.getElementById('day-filter');
    const saveBtn = document.getElementById('save-btn');
    const exportBtn = document.getElementById('export-btn');

    currentDayIndex = getTodayIndex();
    dayFilter.value = currentDayIndex.toString();

    loadWeeklySchedule();

    dayFilter.addEventListener('change', () => {
        currentDayIndex = parseInt(dayFilter.value);
        renderScheduleTable();
    });

    roomFilter.addEventListener('change', () => {
        renderScheduleTable();
    });

    saveBtn.addEventListener('click', saveScheduleData);
    exportBtn.addEventListener('click', exportSchedule);
});

// ---- Helpers ----
function getTodayIndex() {
    const jsIndex = new Date().getDay(); // 0 = Sun
    return jsIndex === 0 ? 6 : jsIndex - 1;
}

// ---- Load full week ----
async function loadWeeklySchedule() {
    try {
        document.getElementById('schedule-body').innerHTML =
            `<tr><td colspan="4" style="text-align:center;padding:20px;">Loading weekly schedule...</td></tr>`;

        let now = new Date();
        // Formats it to yyyy/mm/dd
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        now = `${year}-${month}-${day}`;

        const response = await fetch(`/api/files/get/${FileCFID}/scheduling/fetch/week/${now}`);
        if (!response.ok) throw new Error(`Failed to load week: ${response.statusText}`);

        weeklyScheduleData = await response.json();

        if (!weeklyScheduleData || Object.keys(weeklyScheduleData).length < 7) {
            throw new Error("Invalid weekly data returned");
        }

        renderScheduleTable();
    } catch (err) {
        console.error(err);
        showStatus(`Error loading weekly schedule: ${err.message}`, "error");
    }
}

// ---- Render table for current week ----
function renderScheduleTable() {
    const scheduleBody = document.getElementById("schedule-body");
    const times = generateTimeSlots();

    const dayKey = Object.keys(weeklyScheduleData)[currentDayIndex];
    const dayData = weeklyScheduleData[dayKey] || {};

    const selectedRoom = document.getElementById("room-filter").value;

    let html = "";

    times.forEach(time => {
        // Find the entry matching the selected room
        let storedItem = null;

        if (selectedRoom === "all") {
            // If all rooms, take the first available entry for the slot
            storedItem = dayData[time] || { time, activity: "", auditor: "", room: "" };
        } else {
            // Filter by room
            storedItem = Object.values(dayData).find(item => item.time === time && item.room === selectedRoom);
            if (!storedItem) storedItem = { time, activity: "", auditor: "", room: selectedRoom };
        }

        const displayActivity = storedItem.activity || "\u2014";
        const displayAuditor = storedItem.auditor || "\u2014";

        html += `
        <tr data-time="${time}" data-room="${storedItem.room}">
            <td class="time-col">${time}</td>
            <td class="activity-col editable-field" data-field="activity">${displayActivity}</td>
            <td class="auditor-col editable-field" data-field="auditor">${displayAuditor}</td>
        </tr>`;
    });

    scheduleBody.innerHTML = html;

    initializeEditableFields();
}

// ---- Editable fields ----
function initializeEditableFields() {
    document.querySelectorAll(".editable-field").forEach(field => {
        field.addEventListener("click", function() {
            const row = this.closest("tr");
            const time = row.getAttribute("data-time");
            const fieldType = this.getAttribute("data-field");
            const currentValue = this.textContent === "\u2014" ? "" : this.textContent;

            this.innerHTML = `<input type="text" class="edit-input" value="${currentValue}" data-original="${currentValue}">`;

            const input = this.querySelector(".edit-input");
            input.focus();
            input.select();

            input.addEventListener("blur", () => finishEditing(input, time, fieldType));
            input.addEventListener("keypress", e => {
                if (e.key === "Enter") input.blur();
            });
        });
    });
}

function finishEditing(input, time, fieldType) {
    const newValue = input.value.trim();
    const originalValue = input.getAttribute("data-original");
    const cell = input.closest("td");
    const dayKey = Object.keys(weeklyScheduleData)[currentDayIndex];

    if (!weeklyScheduleData[dayKey][time])
        weeklyScheduleData[dayKey][time] = { time, activity: "", auditor: "", room: "" };

    if (newValue !== originalValue) {
        weeklyScheduleData[dayKey][time][fieldType] = newValue;
        hasUnsavedChanges = true;
        updateSaveButton();

        cell.textContent = newValue || "\u2014";

        if (fieldType === "room") {
            const row = cell.closest("tr");
            row.setAttribute("data-room", newValue);
        }

        sendEditToAPI(dayKey, time, fieldType, newValue);
    } else {
        cell.textContent = originalValue || "\u2014";
    }
}

// ---- Send a single edit to the API ----
async function sendEditToAPI(dayKey, time, field, value) {
    try {
        const payload = { time };

        let room = document.getElementById("room-filter").value;
        if (room === "all") {
            showStatus("Invalid room. Select a room other than 'all'", "error");
            return;
        }

        payload[field] = value;
        payload['cfid'] = FileCFID;
        payload['room'] = room;

        const response = await fetch(`/api/files/get/${FileCFID}/scheduling/save/cell/${dayKey}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error(`Failed to save edit: ${response.statusText}`);

        showStatus("Edit saved!", "success");
        setTimeout(hideStatus, 1000);
        hasUnsavedChanges = false;
        updateSaveButton();
    } catch (err) {
        console.error(err);
        showStatus(`Error saving edit: ${err.message}`, "error");
    }
}

// ---- Save only CURRENT day ----
async function saveScheduleData() {
    try {
        showStatus("Saving...", "info");

        const dayKey = Object.keys(weeklyScheduleData)[currentDayIndex];
        const dataToSave = weeklyScheduleData[dayKey];

        const response = await fetch(`/api/files/get/${FileCFID}/scheduling/save/day/${dayKey}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(dataToSave)
        });

        if (!response.ok) throw new Error(`Failed: ${response.statusText}`);

        hasUnsavedChanges = false;
        updateSaveButton();
        showStatus("Saved!", "success");

        setTimeout(hideStatus, 1500);
    } catch (err) {
        showStatus(`Error: ${err.message}`, "error");
    }
}

// ---- Export ----
function exportSchedule() {
    const dataStr = JSON.stringify(weeklyScheduleData, null, 2);
    const blob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = `weekly-schedule-${FileCFID}.json`;
    link.click();

    URL.revokeObjectURL(url);
}

// ---- UI helpers ----
function updateSaveButton() {
    document.getElementById("save-btn").disabled = !hasUnsavedChanges;
}

function showStatus(msg, type) {
    const el = document.getElementById("status-message");
    el.textContent = msg;
    el.className = `status-message status-${type}`;
    el.style.display = "block";
}

function hideStatus() {
    document.getElementById("status-message").style.display = "none";
}

// ---- Generate 24 hours ----
function generateTimeSlots() {
    const times = [];
    for (let h = 0; h < 24; h++) {
        const period = h >= 12 ? "PM" : "AM";
        const displayHour = (h % 12) || 12;
        times.push(`${displayHour}:00 ${period}`);
    }
    return times;
}

