let theta_display = document.getElementById('theta_display');
let theta_field = document.getElementById('field-theta_endowment');
let debounceTimer = null;

function updateThetaDisplay(val) {
    theta_display.textContent = val;
}

theta_field.addEventListener('input', () => {
    const val = theta_field.value;
    updateThetaDisplay(val);

    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
        sendThetaValue(val);
    }, 800);
});

function sendThetaValue(theta_count) {
    fetch('/api/files/set_theta', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            cfid: FileCFID,
            theta_count: Number(theta_count)
        })
    }).catch(err => console.error('Error sending theta value:', err));
}

function moveSliderToSavedLevel() {
    theta_field.value = theta_endowment;
}

document.addEventListener('DOMContentLoaded', moveSliderToSavedLevel);