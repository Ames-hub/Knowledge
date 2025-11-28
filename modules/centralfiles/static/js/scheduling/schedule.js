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

    roomFilter.addEventListener('change', filterSchedule);
    dayFilter.addEventListener('change', () => {
        currentDayIndex = parseInt(dayFilter.value);
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

function getWeekStartDate() {
    const now = new Date();
    const jsIndex = now.getDay(); // 0 = Sun
    const mondayOffset = jsIndex === 0 ? -6 : 1 - jsIndex;
    const monday = new Date(now);
    monday.setDate(now.getDate() + mondayOffset);
    return monday.toISOString().split("T")[0];
}

// ---- Load full week ----
async function loadWeeklySchedule() {
    try {
        document.getElementById('schedule-body').innerHTML =
            `<tr><td colspan="4" style="text-align:center;padding:20px;">Loading weekly schedule...</td></tr>`;

        const weekStart = getWeekStartDate();

        const response = await fetch(`/api/files/get/${FileCFID}/scheduling/fetch/week/${weekStart}`);
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

// ---- Render table for current day ----
function renderScheduleTable() {
    const scheduleBody = document.getElementById("schedule-body");
    const times = generateTimeSlots();

    const dayKey = Object.keys(weeklyScheduleData)[currentDayIndex];
    const scheduleData = weeklyScheduleData[dayKey] || {};

    let html = "";

    times.forEach(time => {
        const item = scheduleData[time] || {
            time,
            activity: "",
            auditor: "",
            room: ""
        };

        const roomValue = item.room.toLowerCase().replace(/[^a-z0-9]/g, "");

        html += `
        <tr data-time="${time}" data-room="${roomValue}">
            <td class="time-col">${time}</td>
            <td class="activity-col editable-field" data-field="activity">${item.activity || "\u2014"}</td>
            <td class="auditor-col editable-field" data-field="auditor">${item.auditor || "\u2014"}</td>
            <td class="room-col editable-field" data-field="room">${item.room || "\u2014"}</td>
        </tr>`;
    });

    scheduleBody.innerHTML = html;

    initializeEditableFields();
    filterSchedule();
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
            row.setAttribute("data-room", newValue.toLowerCase().replace(/[^a-z0-9]/g, ""));
        }
    } else {
        cell.textContent = originalValue || "\u2014";
    }
}

// ---- Filtering ----
function filterSchedule() {
    const selectedRoom = document.getElementById("room-filter").value;
    const rows = document.querySelectorAll("#schedule-body tr");

    rows.forEach(row => {
        if (selectedRoom === "all" || row.getAttribute("data-room") === selectedRoom) {
            row.style.display = "";
        } else {
            row.style.display = "none";
        }
    });
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
