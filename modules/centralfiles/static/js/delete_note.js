async function deleteNote(noteId) {
    const confirmed = confirm("Are you sure you want to delete this note?");
    if (!confirmed) return;

    try {
        const res = await fetch("/api/files/note/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ note_id: parseInt(noteId) })
        });

        if (res.ok) {
            const block = document.getElementById(`note-block-${noteId}`);
            if (block) block.remove();
        } else {
            alert("Failed to delete the note.");
        }
    } catch (err) {
        console.error("Error deleting note:", err);
        alert("Error deleting note.");
    }
}
