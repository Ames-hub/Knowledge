const trackModal = document.getElementById('trackModal');
const payModal = document.getElementById('payModal');

document.getElementById('openTrackModal').onclick = () => trackModal.style.display = 'block';
document.getElementById('closeTrackModal').onclick = () => trackModal.style.display = 'none';

document.getElementById('openPayModal').onclick = () => payModal.style.display = 'block';
document.getElementById('closePayModal').onclick = () => payModal.style.display = 'none';

// Close modal if user clicks outside content
window.onclick = function(event) {
    if (event.target == trackModal) trackModal.style.display = "none";
    if (event.target == payModal) payModal.style.display = "none";
}

// Example: handle form submissions (currently just logs to console)
document.getElementById('trackDebtForm').onsubmit = function(e) {
    e.preventDefault();
    console.log("New debt:", Object.fromEntries(new FormData(this).entries()));
    trackModal.style.display = 'none';
    this.reset();
}

document.getElementById('payDebtForm').onsubmit = function(e) {
    e.preventDefault();
    console.log("Debt payment:", Object.fromEntries(new FormData(this).entries()));
    payModal.style.display = 'none';
    this.reset();
}