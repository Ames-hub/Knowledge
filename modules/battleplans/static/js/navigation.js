// ==================== Navigation ====================
const backBtn = document.getElementById("back-btn");
backBtn.addEventListener("click", () => window.location.href = "/");

const bplist = document.getElementById("bplist");
const toggleBtn = document.getElementById("toggle-bplist-btn");
const plansContainer = document.getElementById("plans-container");

function setOpenState(open) {
  if (open) {
    toggleBtn.setAttribute("aria-expanded", "true");
    bplist.removeAttribute("aria-hidden");
    bplist.removeAttribute("hidden");
    toggleBtn.textContent = "✕";
  } else {
    toggleBtn.setAttribute("aria-expanded", "false");
    bplist.setAttribute("aria-hidden", "true");
    toggleBtn.textContent = "☰";
  }
}

toggleBtn.addEventListener("click", () => {
  const isOpen = toggleBtn.getAttribute("aria-expanded") === "true";
  setOpenState(!isOpen);
});

if (window.innerWidth < 900) setOpenState(false);
else setOpenState(true);

// Theme toggle
const btn = document.getElementById("theme-toggle-btn");
btn.addEventListener("click", () => {
  const theme = document.body.dataset.theme === "light" ? "dark" : "light";
  document.body.dataset.theme = theme;
  localStorage.setItem("theme", theme);
});
document.body.dataset.theme = localStorage.getItem("theme") || "dark";
