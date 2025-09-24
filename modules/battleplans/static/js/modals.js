// Warning modal
const warningModal = document.getElementById("bp-warning-modal");
const warningCancel = document.getElementById("bp-warning-cancel");
const warningConfirm = document.getElementById("bp-warning-confirm");
const helpBtn = document.getElementById("help-btn");

function showWarningModal() {
  return new Promise((resolve) => {
    warningModal.classList.remove("hidden");
    const cleanup = () => {
      warningModal.classList.add("hidden");
      warningCancel.removeEventListener("click", onCancel);
      warningConfirm.removeEventListener("click", onConfirm);
    };
    function onCancel() { cleanup(); resolve(false); }
    function onConfirm() {
      cleanup();
      localStorage.setItem("bpWarningDismissedUntil", Date.now() + 30*60*1000);
      resolve(true);
    }
    warningCancel.addEventListener("click", onCancel);
    warningConfirm.addEventListener("click", onConfirm);
  });
}
function shouldShowWarning(dateStr) {
  const today = getTodayStr();
  if (dateStr === today) return false;
  const dismissedUntil = parseInt(localStorage.getItem("bpWarningDismissedUntil") || "0", 10);
  return Date.now() > dismissedUntil;
}

// Help modal
const helpModal = document.getElementById("bp-help-modal");
const helpClose = document.getElementById("bp-help-close");
helpBtn.addEventListener("click", () => helpModal.classList.remove("hidden"));
helpClose.addEventListener("click", () => helpModal.classList.add("hidden"));
