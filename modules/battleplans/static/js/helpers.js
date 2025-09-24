// helpers.js
const doNotifySuccess = true;

function getTodayStr() {
  const now = new Date();
  const day = String(now.getDate()).padStart(2, "0");
  const month = now.toLocaleString("default", { month: "long" });
  const year = now.getFullYear();
  return `${day}-${month}-${year}`;
}

function debounce(fn, wait = 700) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
}

// Guard function for editing BPs
async function ensureEditAllowed(target) {
  if (!shouldShowWarning(currentBPDate)) return true;

  const proceed = await showWarningModal();
  if (!proceed) {
    if (target) {
      target.blur();
      if ("checked" in target) target.checked = !target.checked;
      if ("value" in target) target.value = target.defaultValue || "";
    }
    return false;
  }
  return true;
}

function parseDateStr(dateStr) {
  const parts = dateStr.split("-");
  return { day: parts[0], month: parts[1] };
}