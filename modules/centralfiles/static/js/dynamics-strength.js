const dynamics = [
    { id: "dynamic-self", name: "Self" },
    { id: "dynamic-sex-family", name: "Sex and Family" },
    { id: "dynamic-groups", name: "Groups" },
    { id: "dynamic-mankind", name: "Mankind" }
];

// Map numeric strength to string values
const strengthMap = {
    0: "undecided",
    1: "short",
    2: "medium",
    3: "long"
};

// Map backend dynamic numbers to names
const dynNumberToName = {
    1: "Self",
    2: "Sex and Family",
    3: "Groups",
    4: "Mankind"
};

// Function to load strengths from the API
async function loadStrengths() {
    try {
        const response = await fetch(`/api/dianetics/dianometry/dyn_strengths/get/${FileCFID}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch strengths: ${response.statusText}`);
        }

        const data = await response.json();

        data.forEach(entry => {
            const name = dynNumberToName[entry.dynamic];
            const dynamic = dynamics.find(d => d.name === name);
            if (dynamic) {
                const select = document.getElementById(dynamic.id);
                // Map -1 or 0 from backend to "0" for the dropdown
                const strengthValue = entry.strength <= 0 ? "0" : entry.strength.toString();
                select.value = strengthValue;
            }
        });

    } catch (err) {
        console.error("Error loading dynamic strengths:", err);
    }
}

// Attach change listeners to send updates
dynamics.forEach(dynamic => {
    const select = document.getElementById(dynamic.id);
    select.addEventListener("change", async () => {
        const value = select.value; // "0", "1", "2", "3"
        
        try {
            const response = await fetch("/api/dianetics/dianometry/dyn_strengths/set", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    dynamic: dynamic.name,
                    strength: value,
                    cfid: FileCFID
                })
            });

            if (!response.ok) {
                console.error(`Failed to update ${dynamic.name}:`, response.statusText);
            } else {
                console.log(`${dynamic.name} updated to ${strengthMap[value]}`);
            }
        } catch (err) {
            console.error(`Error updating ${dynamic.name}:`, err);
        }
        loadMindClass()
    });
});