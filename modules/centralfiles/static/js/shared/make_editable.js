async function makeEditable(fieldId, cfid, fieldType = 'text') {

    function detectDateFormat() {
        // This function uses how the system parses the date to a string to
        // figure out what the local date format is for the user.
        
        // Use a known date: 12 Nov 2025
        const formatted = new Date(2025, 10, 12).toLocaleDateString();
        const parts = formatted.match(/\d+/g).map(Number);

        // If it begins with year, it's ISO
        if (formatted.trim().startsWith("2025")) {
            return "%Y-%m-%d";
        }

        const month = parts[0];
        const day   = parts[1];

        // MDY if month shows up first
        if (month === 11 && day === 12) {
            return "%m-%d-%Y";
        }

        // Otherwise treat as DMY
        return "%d-%m-%Y";
    }

    const fieldEl = document.getElementById(fieldId);
    const value = fieldEl.innerText.trim();

    // Create appropriate input based on field type
    let input;
    
    switch(fieldType) {
        case 'bool':
            input = document.createElement("select");
            input.innerHTML = `
                <option value="True" ${value === 'True' ? 'selected' : ''}>True</option>
                <option value="False" ${value === 'False' ? 'selected' : ''}>False</option>
            `;
            input.className = "inline-select";
            break;
            
        case 'number':
            input = document.createElement("input");
            input.type = "number";
            input.value = value;
            input.className = "inline-input number-input";
            break;
            
        case 'date':
            input = document.createElement("input");
            input.type = "date";
            input.value = value;
            input.className = "inline-input date-input";
            break;
            
        default: // text
            input = document.createElement("input");
            input.type = "text";
            input.value = value;
            input.className = "inline-input";
    }

    input.onblur = submitEdit;
    input.onkeydown = function(e) {
        if (e.key === "Enter") {
            input.blur();
        }
        if (e.key === "Escape") {
            cancelEdit();
        }
    };

    // Replace and focus
    fieldEl.replaceWith(input);
    input.focus();

    function cancelEdit() {
        const newSpan = document.createElement("span");
        newSpan.id = fieldId;
        newSpan.className = "editable";
        newSpan.innerText = value;
        newSpan.onclick = () => makeEditable(fieldId, cfid, fieldType);
        input.replaceWith(newSpan);
    }

    async function submitEdit() {
        let newValue;
        
        // Get value based on input type
        if (fieldType === 'bool') {
            newValue = input.value;
        } else {
            newValue = input.value.trim();
        }

        // Validation based on field type
        let isValid = true;
        let displayedValue = newValue

        switch(fieldType) {
            case 'bool':
                isValid = newValue === 'True' || newValue === 'False';
                if (!isValid) {
                    cancelEdit()
                }
                break;
                
            case 'number':
                isValid = !isNaN(newValue);
                if (!isValid) {
                    alert("Please enter a valid number");
                    input.focus();
                    return;
                }
                break;
                
            case 'date':
                isValid = newValue !== '';
                if (!isValid) {
                    cancelEdit()
                    return;
                }

                // When the new value is a date, reformat it from ISO to the detected local format
                const fmt = detectDateFormat();
                const isoParts = newValue.split('-'); // expected YYYY-MM-DD
                if (isoParts.length === 3) {
                    const [yyyy, mm, dd] = isoParts;
                    if (fmt === "%Y-%m-%d") {
                        displayedValue = `${yyyy}/${mm}/${dd}`;
                    } else if (fmt === "%m-%d-%Y") {
                        displayedValue = `${mm}/${dd}/${yyyy}`;
                    } else { // treat as "%d-%m-%Y" or fallback
                        displayedValue = `${dd}/${mm}/${yyyy}`;
                    }
                } else {
                    displayedValue = newValue;
                }

                break;
                
            default:
                isValid = newValue !== '';
        }

        if (!isValid) {
            alert(`Please enter a valid ${fieldType} value`);
            input.focus();
            return;
        }

        const newSpan = document.createElement("span");
        newSpan.id = fieldId;
        newSpan.className = "editable";
        newSpan.innerText = displayedValue;
        newSpan.onclick = () => makeEditable(fieldId, cfid, fieldType);

        input.replaceWith(newSpan);

        // Build payload for server
        const payload = {
            cfid: cfid,
            field: fieldId.replace("field-", ""),
            value: newValue,
        };

        // Send update to server
        await fetch(`/api/files/modify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
    }
}
