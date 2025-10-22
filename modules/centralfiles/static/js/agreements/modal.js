const agreementModal = document.getElementById('agreementModal');
const agreementTextInput = document.getElementById('agreement-text');
const agreementDateInput = document.getElementById('agreement-date');
const cancelBtn = document.getElementById('agreement-cancel-btn');
const submitBtn = document.getElementById('agreement-submit-btn');

let currentCFID = null;

// Open modal
function createNewAgreement(cfid) {
    currentCFID = cfid;
    agreementTextInput.value = '';
    agreementDateInput.value = '';
    agreementModal.style.display = 'flex';
}

// Close modal
function closeAgreementModal() {
    agreementModal.style.display = 'none';
    currentCFID = null;
}

cancelBtn.addEventListener('click', closeAgreementModal);

// Submit modal
submitBtn.addEventListener('click', async () => {
    const agreementText = agreementTextInput.value.trim();
    const datePromised = agreementDateInput.value;

    if (!agreementText || !datePromised) {
        alert('Please fill out all fields.');
        return;
    }

    try {
        const resp = await fetch(`/api/files/${currentCFID}/agreements/add`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                agreement: agreementText,
                date_promised: datePromised
            })
        });

        if (!resp.ok) throw new Error('Failed to add agreement.');

        // Add new row to table
        const table = document.querySelector('.left-column table');
        const newRow = table.insertRow();
        const fulfilledCell = newRow.insertCell(0);
        fulfilledCell.innerHTML = '<input type="checkbox">';
        const dateCell = newRow.insertCell(1);
        dateCell.textContent = new Date(datePromised).toLocaleString();
        const agreementCell = newRow.insertCell(2);
        agreementCell.textContent = agreementText;

        closeAgreementModal();
    } catch (err) {
        alert(err.message);
    }
});
