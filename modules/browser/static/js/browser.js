 // Function to get cookie by name
 function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';')[0];
}

(function () {
    const cards = Array.from(document.querySelectorAll('.app-card'));
    const themeToggle = document.getElementById('theme-toggle');
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const savedTheme = localStorage.getItem('theme');

    // Initialize theme
    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
    document.documentElement.classList.add('theme-dark');
    }

    themeToggle.addEventListener('click', () => {
    document.documentElement.classList.toggle('theme-dark');
    localStorage.setItem('theme', document.documentElement.classList.contains('theme-dark') ? 'dark' : 'light');
    });
})();

let logout_btn = document.getElementById("logout-btn")
logout_btn.addEventListener('click', () => {
    // Clears all cookies
    document.cookie.split(";").forEach(cookie => {
        const eqPos = cookie.indexOf("=");
        const name = eqPos > -1 ? cookie.substr(0, eqPos).trim() : cookie.trim();
        document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/";
    });
    window.location = "/login"
});