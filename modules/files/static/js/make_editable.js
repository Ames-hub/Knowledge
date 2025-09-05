async function makeEditable(fieldId, cfid) {
    const fieldEl = document.getElementById(fieldId);
    const value = fieldEl.innerText.trim();

    // Replace span with input
    const input = document.createElement("input");
    input.type = "text";
    input.value = value;
    input.className = "inline-input";
    input.onblur = submitEdit;
    input.onkeydown = function(e) {
        if (e.key === "Enter") {
            input.blur();
        }
    };

    // Replace and focus
    fieldEl.replaceWith(input);
    input.focus();

    async function submitEdit() {
        const newValue = input.value.trim();
        const newSpan = document.createElement("span");
        newSpan.id = fieldId;
        newSpan.className = "editable";
        newSpan.innerText = newValue;
        newSpan.onclick = () => makeEditable(fieldId, cfid);

        input.replaceWith(newSpan);

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