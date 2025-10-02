document.addEventListener("DOMContentLoaded", async () => {
    const list = document.getElementById("preclear-list");

    try {
        const res = await fetch("/api/dianetics/preclear/list");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const preclears = await res.json();

        if (preclears.length === 0) {
            list.innerHTML = "<li>No preclears found.</li>";
            return;
        }

        preclears.forEach(pc => {
            const li = document.createElement("li");
            const a = document.createElement("a");
            a.href = `/dianetics/dianometry/${pc.cfid}`;
            a.textContent = `${pc.name} (CFID: ${pc.cfid})`;
            li.appendChild(a);
            list.appendChild(li);
        });
    } catch (err) {
        list.innerHTML = `<li>Error loading preclears: ${err.message}</li>`;
    }
});