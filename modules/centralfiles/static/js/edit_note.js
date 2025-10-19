// Call this once after your page loads to set up event handlers on existing notes
function initEditableNotes() {
    document.querySelectorAll(".editable-note").forEach(noteEl => {
        const noteId = noteEl.id.replace("note-", "");
        noteEl.tabIndex = 0;
        noteEl.addEventListener("click", () => editNote(noteId));
        noteEl.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                noteEl.blur();
            }
        });
    });
}

async function editNote(noteId) {
    const noteDiv = document.getElementById(`note-${noteId}`);
    const currentText = noteDiv.innerText.trim();

    // Replace div with textarea
    const textarea = document.createElement("textarea");
    textarea.className = "editable-textarea";
    textarea.value = currentText;

    // Replace and focus
    noteDiv.replaceWith(textarea);
    textarea.focus();

    function finishEditing() {
        const newText = textarea.value.trim();
        const newDiv = document.createElement("div");
        newDiv.id = `note-${noteId}`;
        newDiv.className = "editable-note";
        newDiv.tabIndex = 0;
        newDiv.innerText = newText;
        newDiv.addEventListener("click", () => editNote(noteId));
        newDiv.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                newDiv.blur();
            }
        });

        textarea.replaceWith(newDiv);

        // Send update to server
        fetch("/api/files/note/modify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                note_id: noteId,
                note: newText,
            }),
        }).catch((err) => {
            console.error("Failed to update note:", err);
            alert("Error updating note.");
        });
    }

    textarea.onblur = finishEditing;
    textarea.onkeydown = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            textarea.blur();
        }
    };
}

// Call this function once after DOM is ready to attach events to all notes
document.addEventListener("DOMContentLoaded", initEditableNotes);
