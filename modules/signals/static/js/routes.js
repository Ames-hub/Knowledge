// routes.js
const sigContainer = document.getElementById("sig-container");
const signalItem = document.getElementById("signal-item");
const searchBar = document.getElementById("search-bar");

const saveBtn = document.getElementById("save-btn");
const closeBtn = document.getElementById("close-btn");
const openBtn = document.getElementById("open-btn");
const delBtn = document.getElementById("del-btn");
const addPlanBtn = document.getElementById("add-plan-btn");

let currentSignal = null;

// Helper for API requests
async function apiRequest(url, method = "GET", data = null) {
  const options = { method };
  if (data) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(data);
  }
  const resp = await fetch(url, options);
  if (resp.headers.get("content-type")?.includes("application/json")) {
    return await resp.json();
  }
  return await resp.text();
}

// Load all signals
async function loadSignals() {
  const signals = await apiRequest("/api/signals/list");
  sigContainer.innerHTML = "";

  Object.values(signals).forEach(signal => {
    const btn = document.createElement("button");
    btn.textContent = signal.route + (signal.closed ? " (Closed)" : "");
    btn.addEventListener("click", () => loadSignal(signal.route));
    sigContainer.appendChild(btn);
  });
}

// Load a single signal into the editor
async function loadSignal(route) {
  const data = await apiRequest("/api/signals/load", "POST", { signal_route: route });

  if (data.message) {
    toast(data.message);
    return;
  }

  const fetched_data = await apiRequest(`/api/signals/datafetch/${data.route}`, "GET").then(
    res => typeof res === "string" ? res : JSON.stringify(res)
  );

  currentSignal = data;
  signalItem.innerHTML = `
    <label>Route: <input id="route-input" value="${data.route}" disabled></label>
    <label>HTTP Code: <input id="http-input" type="number" value="${data.http_code}"></label>
    <label>Route Function: <input id="func-input" value="${data.route_func}.py"></label>
    <label>HTML Response:</label>
    <textarea id="html-input" rows="10">${data.html_response}</textarea>
    <p id='status_label'>Status: ${data.closed ? "Closed" : "Open"}</p>
    <p>${fetched_data}</p>
    <a href="/api/signals/r/${data.route}" target="_blank">Test Route</a>
  `;
}

// Save current signal
saveBtn.addEventListener("click", async () => {
  if (!currentSignal) return toast("No signal loaded!");

  const route = currentSignal.route;
  const httpCode = parseInt(document.getElementById("http-input").value);
  const htmlResponse = document.getElementById("html-input").value;

  let success = await apiRequest("/api/signals/save/code", "POST", { signal_route: route, http_code: httpCode });
  if (typeof success === "string" && success.includes("Failure")) return toast("Failed to save HTTP code.");

  success = await apiRequest("/api/signals/save/html", "POST", { signal_route: route, html_response: htmlResponse });
  if (typeof success === "string" && success.includes("Failure")) return toast("Failed to save HTML.");

  toast("Signal saved!");
  loadSignals();
});

// Close route
closeBtn.addEventListener("click", async () => {
  if (!currentSignal) return toast("No signal loaded!");
  
  await apiRequest(`/api/signals/close/${currentSignal.route}`, "POST");
  
  toast("Route closed!");
  
  let status_label = document.getElementById('status_label');
  status_label.innerText = "Status: Closed";

  loadSignals();
});

// Open route
openBtn.addEventListener("click", async () => {
  if (!currentSignal) return toast("No signal loaded!");
  
  await apiRequest(`/api/signals/open/${currentSignal.route}`, "POST");
  
  toast("Route opened!");
  
  let status_label = document.getElementById('status_label');
  status_label.innerText = "Status: Open";

  loadSignals();
});

// Delete route
delBtn.addEventListener("click", async () => {
  if (!currentSignal) return toast("No signal loaded!");
  if (!confirm("Are you sure you want to delete this route?")) return;
  await apiRequest(`/api/signals/delete`, "POST", {'signal_route': currentSignal.route});
  currentSignal = null;
  signalItem.innerHTML = "";
  toast("Route deleted!");
  loadSignals();
});

// Modal elements (assumes modal exists in HTML)
const newRouteModal = document.getElementById("new-route-modal");
const closeModalBtn = document.getElementById("close-modal");
const createRouteBtn = document.getElementById("create-route-btn");

// Open modal
addPlanBtn.addEventListener("click", () => {
  newRouteModal.style.display = "flex";
});

// Close modal
closeModalBtn.addEventListener("click", () => {
  newRouteModal.style.display = "none";
});

window.addEventListener("click", (e) => {
  if (e.target === newRouteModal) newRouteModal.style.display = "none";
});

// Handle creating new route
createRouteBtn.addEventListener("click", async () => {
  const route = document.getElementById("new-route-path").value.trim();
  const httpCode = parseInt(document.getElementById("new-route-http").value) || 200;
  const htmlResponse = document.getElementById("new-route-html").value;
  const routeFunc = document.getElementById("new-route-func").value.trim() || "None";

  if (!route) return toast("Route path cannot be empty!");

  const res = await apiRequest("/api/signals/mknew", "POST", { signal_route: route, http_code: httpCode, html_response: htmlResponse, route_func: routeFunc });
  toast(res);
  newRouteModal.style.display = "none";

  // Reset modal fields
  document.getElementById("new-route-path").value = "";
  document.getElementById("new-route-http").value = 200;
  document.getElementById("new-route-html").value = "<h1>New Route! <func_response></h1>";
  document.getElementById("new-route-func").value = "None";

  loadSignals();
});

// Search filter
searchBar.addEventListener("input", () => {
  const query = searchBar.value.toLowerCase();
  Array.from(sigContainer.children).forEach(btn => {
    btn.style.display = btn.textContent.toLowerCase().includes(query) ? "block" : "none";
  });
});

// Initial load
loadSignals();
