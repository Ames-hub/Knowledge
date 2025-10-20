async function loadMindClass() {
    const container = document.getElementById("mindclass_estimation");
    const actualLevelSpan = document.getElementById("estimated-actual-level");
    const apparentLevelSpan = document.getElementById("estimated-apparent-level");

    try {
        const response = await fetch(`/api/dianetics/dianometry/get_mind_class/${FileCFID}`);
        if (!response.ok) throw new Error(`Failed to fetch mind class: ${response.statusText}`);

        const data = await response.json();
        // Update both spans
        actualLevelSpan.textContent = data.actual ?? "N/A";
        apparentLevelSpan.textContent = data.apparent ?? "N/A";

        // Make sure the panel is visible
        container.classList.remove("hidden");

    } catch (err) {
        console.error("Error loading mind class:", err);
        actualLevelSpan.textContent = "Error";
        apparentLevelSpan.textContent = "Error";
        container.classList.remove("hidden");
    }
}

loadMindClass()