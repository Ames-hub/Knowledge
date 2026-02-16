async function makeEditable(fieldId, cfid, fieldType = 'text', options = []) {

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

        case 'dropdown-text':
            input = document.createElement("select");
            input.className = "inline-select";

            options.forEach(opt => {
                const optionEl = document.createElement("option");
                optionEl.value = opt;
                optionEl.textContent = opt;
                if (opt === value) {
                    optionEl.selected = true;
                }
                input.appendChild(optionEl);
            });
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
                
            case 'dropdown-text':
                isValid = options.includes(newValue);
                if (!isValid) {
                    cancelEdit();
                    return;
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

        // Create the new span with the new value (temporarily)
        const newSpan = document.createElement("span");
        newSpan.id = fieldId;
        newSpan.className = "editable";
        newSpan.innerText = displayedValue;
        newSpan.onclick = () => makeEditable(fieldId, cfid, fieldType, options);

        // Replace input with the new span (show optimistic update)
        input.replaceWith(newSpan);

        // Build payload for server
        const payload = {
            cfid: cfid,
            field: fieldId.replace("field-", ""),
            value: newValue,
        };

        // Send update to server
        const response = await fetch(`/api/files/modify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        // Check if response is not OK (status code not in 200-299 range)
        if (!response.ok) {
            try {
                const errorData = await response.json();
                // Display error message from server response, or use status text as fallback
                const errorMessage = errorData.message || errorData.error || `Error: ${response.status} ${response.statusText}`;
                alert(`${errorMessage}`);
                
                // UNDO THE CHANGE: Revert back to original value
                const originalSpan = document.createElement("span");
                originalSpan.id = fieldId;
                originalSpan.className = "editable";
                originalSpan.innerText = value; // Use original value from outer scope
                originalSpan.onclick = () => makeEditable(fieldId, cfid, fieldType, options);
                newSpan.replaceWith(originalSpan);
                
            } catch (e) {
                // If response is not valid JSON, show generic error with status
                alert(`Update failed: ${response.status} ${response.statusText}`);
                
                // UNDO THE CHANGE: Revert back to original value
                const originalSpan = document.createElement("span");
                originalSpan.id = fieldId;
                originalSpan.className = "editable";
                originalSpan.innerText = value; // Use original value from outer scope
                originalSpan.onclick = () => makeEditable(fieldId, cfid, fieldType, options);
                newSpan.replaceWith(originalSpan);
            }
        } else {
            if (fieldId === "field-is_dianetics") {
                location.reload();  // Reload the page to show changes
            }
        }
    }
}
