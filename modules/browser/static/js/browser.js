 // Function to get cookie by name
 function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';')[0];
}


(function () {
    const username = getCookie("username");
    const splash = document.getElementById('splash_text');
    const search = document.getElementById('app-search');
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

    // Small splash text animation (non-intrusive)
    const messages = [
    `Hello, ${username}.`,
    'Keyboard friendly: Tab → Enter.',
    'Try searching apps above.',
    'Swipe on mobile to browse.'
    ];
    let idx = 0;
    let lastSwitch = Date.now();

    function rotateSplash() {
    if (document.hidden) return;
    const now = Date.now();
    if (now - lastSwitch > 4000) {
        idx = (idx + 1) % messages.length;
        splash.textContent = messages[idx];
        lastSwitch = now;
    }
    requestAnimationFrame(rotateSplash);
    }
    requestAnimationFrame(rotateSplash);

    // Search filter
    search.addEventListener('input', (e) => {
    const q = e.target.value.trim().toLowerCase();
    cards.forEach(card => {
        const name = (card.querySelector('.app-name') || {textContent: ''}).textContent.toLowerCase();
        card.hidden = q && !name.includes(q);
    });
    });

    // Keyboard — Enter to open, arrow keys to move on mobile horizontal layout as convenience
    document.addEventListener('keydown', (ev) => {
    const active = document.activeElement;
    if (ev.key === 'Enter' && active && active.classList.contains('app-card')) {
        active.click();
    }

    // Left/right navigation when a card is focused or search is focused and on small screens
    if ((ev.key === 'ArrowRight' || ev.key === 'ArrowLeft')) {
        const isMobile = window.matchMedia('(max-width: 600px)').matches;
        if (!isMobile) return;
        const focusedIndex = cards.indexOf(document.activeElement);
        if (focusedIndex >= 0) {
        const next = ev.key === 'ArrowRight' ? focusedIndex + 1 : focusedIndex - 1;
        const target = cards[(next + cards.length) % cards.length];
        if (target) {
            target.focus();
            target.scrollIntoView({behavior: 'smooth', inline: 'center', block: 'nearest'});
            ev.preventDefault();
        }
        }
    }
    });

    // Improve focus outline visibility for keyboard users
    document.body.addEventListener('mousedown', () => document.documentElement.classList.add('using-mouse'));
    document.body.addEventListener('keydown', () => document.documentElement.classList.remove('using-mouse'));
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