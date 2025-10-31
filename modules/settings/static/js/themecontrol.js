// Theme toggle logic
const toggle = document.getElementById('theme-toggle');
const root = document.documentElement;

function setTheme(mode) {
    root.setAttribute('data-theme', mode);
    localStorage.setItem('theme', mode);
}

// Load preferred theme
const saved = localStorage.getItem('theme');
if (saved) {
    setTheme(saved);
} else if (window.matchMedia('(prefers-color-scheme: light)').matches) {
    setTheme('light');
}

toggle.addEventListener('click', () => {
    const current = root.getAttribute('data-theme');
    setTheme(current === 'dark' ? 'light' : 'dark');
});