

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("form");

    form.addEventListener("submit", async (event) => {
        event.preventDefault(); // Stop the form from reloading the page

        const formData = new FormData(form);
        const payload = {
            username: formData.get("username"),
            password: formData.get("password"),
        };

        try {
            const response = await fetch("/api/authbook/register", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                console.log("Registration failed:", response);
            }

            const data = await response.json();

            if (response.status === 400 || response.status == 403) {
                toast(data['error']);
                return
            }
            console.log("Registration successful:", data);

            // Optionally redirect or show a message
            window.location.href = "/login";
        } catch (err) {
            console.error("Error:", err);
            alert("Registration failed.");
        }
    });
});

// Apply theme
function applyTheme(theme){
if(theme === 'dark'){
    document.body.classList.add('theme-dark');
    document.body.classList.remove('theme-light');
    document.getElementById('theme-toggle-register').textContent = '☀️ Switch Theme';
} else {
    document.body.classList.add('theme-light');
    document.body.classList.remove('theme-dark');
    document.getElementById('theme-toggle-register').textContent = '🌙 Switch Theme';
}
}

// Load theme from localStorage
const savedTheme = localStorage.getItem('theme') || 'light';
applyTheme(savedTheme);

// Toggle theme
document.getElementById('theme-toggle-register').addEventListener('click', () => {
    const newTheme = document.body.classList.contains('theme-dark') ? 'light' : 'dark';
    localStorage.setItem('theme', newTheme);
    applyTheme(newTheme);
});