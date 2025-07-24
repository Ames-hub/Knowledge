async function createNewNote(cfid) {
    const defaultText = "Click me to modify your new note!";
    const res = await fetch("/api/files/note/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cfid: cfid, note: defaultText })
    });

    if (!res.ok) {
        alert("Failed to create a new note.");
        return;
    }

    const result = await res.json();
    const noteId = result.note_id;
    // noinspection JSUnresolvedReference
    const addDate = result.add_date;
    // noinspection JSUnresolvedReference
    const author = result.author;

    const noteBlock = document.createElement("div");
    noteBlock.className = "note-entry";
    noteBlock.id = `note-block-${noteId}`;

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.innerText = `${addDate} — ${author}`;

    const noteDiv = document.createElement("div");
    noteDiv.className = "editable-note";
    noteDiv.id = `note-${noteId}`;
    noteDiv.tabIndex = 0;
    noteDiv.innerText = defaultText;
    noteDiv.onclick = () => editNote(noteId);
    noteDiv.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            noteDiv.blur();
        }
    });

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "delete-note-btn";
    deleteBtn.innerText = "🗑️";
    deleteBtn.onclick = () => deleteNote(noteId);

    noteBlock.appendChild(meta);
    noteBlock.appendChild(noteDiv);
    noteBlock.appendChild(deleteBtn);

    document.getElementById("notes-list").prepend(noteBlock);
}
