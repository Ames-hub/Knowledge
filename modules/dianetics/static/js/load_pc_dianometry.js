document.addEventListener("DOMContentLoaded", async () => {
    const select = document.getElementById("preclear-select");
    const infoDiv = document.getElementById("preclear-info");
    const infoName = document.getElementById("info-name");
    const infoCFID = document.getElementById("info-cfid");

    infoDiv.style.display = "block";
    load_chart(selectedCFID);
    loadStrengths();
    loadShutoffs();
    loadMindClass()
});
