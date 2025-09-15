let selectedCFID

document.addEventListener("DOMContentLoaded", async () => {
    const select = document.getElementById("preclear-select");
    const infoDiv = document.getElementById("preclear-info");
    const infoName = document.getElementById("info-name");
    const infoCFID = document.getElementById("info-cfid");
    const chartContainer = document.getElementById("chart-container");
    const dynStrengthSel = document.getElementById("dynamic-strength-selector")
    const shutoffs_chart = document.getElementById("shutoffs_chart")
    const mindclass_estimation = document.getElementById("mindclass_estimation")

    // Hide chart at start
    chartContainer.classList.add("hidden");
    dynStrengthSel.classList.add("hidden");
    shutoffs_chart.classList.add("hidden");
    mindclass_estimation.classList.add("hidden");

    try {
        // Fetch preclears
        const res = await fetch("/api/dianetics/preclear/list");
        const preclears = await res.json();

        // Populate dropdown
        preclears.forEach(pc => {
            const option = document.createElement("option");
            option.value = pc.cfid;
            option.textContent = pc.name;
            select.appendChild(option);
        });
    } catch (err) {
        console.error("Failed to fetch preclears:", err);
        select.innerHTML = '<option value="">Failed to load preclears</option>';
    }

    // When user selects a preclear
    select.addEventListener("change", () => {
        selectedCFID = select.value;
        if (!selectedCFID) {
            infoDiv.style.display = "none";
            chartContainer.classList.add("hidden");
            return;
        }

        // Find selected option
        const selectedOption = select.options[select.selectedIndex];

        infoName.textContent = selectedOption.textContent;
        infoCFID.textContent = selectedCFID;

        infoDiv.style.display = "block";
        chartContainer.classList.remove("hidden");
        dynStrengthSel.classList.remove("hidden");
        shutoffs_chart.classList.remove("hidden");
        mindclass_estimation.classList.remove("hidden");
        load_chart(selectedCFID);
        loadStrengths();
        loadShutoffs();
        loadMindClass()
    });
});
