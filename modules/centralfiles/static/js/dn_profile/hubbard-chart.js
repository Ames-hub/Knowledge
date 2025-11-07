async function load_chart(cfid) {
    const table = document.querySelector(".hubbard-chart");

    // --- Reset state ---
    // Remove all previous highlights
    table.querySelectorAll("td.selected").forEach(cell => {
        cell.classList.remove("selected");
    });

    // Clone table to strip old listeners
    const newTable = table.cloneNode(true);
    table.parentNode.replaceChild(newTable, table);

    // Helper to highlight a cell based on category and tone
    function highlightCell(category, tone) {
        const toneNum = parseFloat(tone);
        newTable.querySelectorAll("tbody tr").forEach(row => {
            const rowCategory = row.querySelector("th.category-cell").innerText.trim();
            if (rowCategory === category) {
                row.querySelectorAll("td").forEach(cell => {
                    const colIndex = cell.cellIndex;
                    const toneLevel = document.querySelector(
                        `.hubbard-chart thead tr th:nth-child(${colIndex + 1})`
                    ).innerText.trim();
                    const cellToneNum = parseFloat(toneLevel);
                    if (!isNaN(toneNum) && !isNaN(cellToneNum) && toneNum === cellToneNum) {
                        cell.classList.add("selected");
                    }
                });
            }
        });
    }

    // Load saved selections from server
    try {
        const resp = await fetch(`/api/dianetics/dianometry/get-chart/${cfid}`);
        if (resp.ok) {
            const saved = await resp.json();
            saved.forEach(entry => highlightCell(entry.column_name, entry.tone_level));
        }
    } catch (err) {
        console.error("Failed to load saved chart:", err);
    }

    // Add click listeners (clean slate now)
    newTable.querySelectorAll("tbody td").forEach(cell => {
        cell.style.cursor = "pointer";

        cell.addEventListener("click", async () => {
            const columnIndex = cell.cellIndex;
            const row = cell.parentElement;
            const toneLevel = newTable.querySelector(
                `.hubbard-chart thead tr th:nth-child(${columnIndex + 1})`
            ).innerText.trim();
            const columnName = row.querySelector("th.category-cell").innerText.trim();

            // Clear existing selection for that row
            row.querySelectorAll("td").forEach(td => td.classList.remove("selected"));
            cell.classList.add("selected");

            // Send update to server
            try {
                const updateResp = await fetch("/api/dianetics/dianometry/update-chart", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        cfid,
                        column_name: columnName,
                        tone_level: toneLevel,
                    }),
                });
                if (!updateResp.ok) throw new Error("Failed to update chart");
                const data = await updateResp.json();
                console.log("Chart updated:", data);
            } catch (err) {
                console.error(err);
                alert("Error updating chart");
            }
        });
    });
}
