async function makeEditable(fieldId, cfid, fieldType = 'text') {
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
            // Convert date format if needed (assuming YYYY-MM-DD for input type="date")
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
        
        switch(fieldType) {
            case 'bool':
                isValid = newValue === 'True' || newValue === 'False';
                break;
                
            case 'number':
                isValid = !isNaN(newValue) && newValue !== '';
                if (!isValid) {
                    alert("Please enter a valid number");
                    input.focus();
                    return;
                }
                break;
                
            case 'date':
                isValid = newValue !== '';
                if (!isValid) {
                    alert("Please select a valid date");
                    input.focus();
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

        const newSpan = document.createElement("span");
        newSpan.id = fieldId;
        newSpan.className = "editable";
        
        // Format display value based on type
        if (fieldType === 'bool') {
            newSpan.innerText = newValue;
        } else if (fieldType === 'date' && newValue) {
            // Format date for display (you might want to keep original format)
            newSpan.innerText = newValue;
        } else {
            newSpan.innerText = newValue;
        }
        
        newSpan.onclick = () => makeEditable(fieldId, cfid, fieldType);

        input.replaceWith(newSpan);

        // Send update to server
        await fetch(`/api/files/modify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                cfid: cfid,
                field: fieldId.replace("field-", ""),
                value: newValue
            })
        });
    }
}