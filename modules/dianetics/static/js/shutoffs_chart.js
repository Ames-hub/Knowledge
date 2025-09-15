const visioCheckbox = document.getElementById("shutoff-visio");
const sonicCheckbox = document.getElementById("shutoff-sonic");

// Update backend when toggled
function updateShutoff(name, value) {
    fetch("/api/dianetics/dianometry/shutoffs/set", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ "name": name, "state": value, "cfid": parseInt(selectedCFID) })
    }).then(res => {
        if (!res.ok) console.error(`Failed to update ${name}`);
        else console.log(`${name} set to ${value}`);
    }).catch(err => console.error(err));
}

document.getElementById("shutoff-visio").addEventListener("change", (e) => {
    visioShutoff = e.target.checked;
    updateShutoff("visio", visioShutoff);
    loadMindClass()
});

document.getElementById("shutoff-sonic").addEventListener("change", (e) => {
    sonicShutoff = e.target.checked;
    updateShutoff("sonic", sonicShutoff);
    loadMindClass()
});

async function loadShutoffs() {
    try {
        const response = await fetch(`/api/dianetics/dianometry/shutoffs/get/${selectedCFID}`);
        if (!response.ok) throw new Error(`Failed to fetch shutoffs: ${response.statusText}`);
        const data = await response.json();

        data.forEach(item => {
            if (item.name === "visio") visioCheckbox.checked = item.state;
            if (item.name === "sonic") sonicCheckbox.checked = item.state;
        });
    } catch (err) {
        console.error("Error loading shutoffs:", err);
    }
}