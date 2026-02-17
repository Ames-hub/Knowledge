// Enhanced mail client with character counters and clear functionality
const form = document.getElementById('mailForm');
const status = document.getElementById('status');
const subjectInput = document.getElementById('subject');
const messageInput = document.getElementById('message');
const subjectCount = document.getElementById('subjectCount');
const messageCount = document.getElementById('messageCount');
const clearBtn = document.getElementById('clearBtn');

// Character counters
function updateSubjectCount() {
    const count = subjectInput.value.length;
    subjectCount.textContent = `${count}/100`;
    subjectCount.className = 'char-count' + (count > 90 ? (count > 95 ? ' danger' : ' warning') : '');
}

function updateMessageCount() {
    const count = messageInput.value.length;
    messageCount.textContent = `${count}/5000`;
    messageCount.className = 'char-count' + (count > 4500 ? (count > 4800 ? ' danger' : ' warning') : '');
}

if (subjectInput) {
    subjectInput.addEventListener('input', updateSubjectCount);
    updateSubjectCount();
}

if (messageInput) {
    messageInput.addEventListener('input', updateMessageCount);
    updateMessageCount();
}

// Clear form
if (clearBtn) {
    clearBtn.addEventListener('click', () => {
    if (confirm('Clear all fields?')) {
        form.reset();
        updateSubjectCount();
        updateMessageCount();
        status.style.display = 'none';
    }
    });
}

// Form submission
form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Show sending status
    status.style.display = 'block';
    status.className = 'status-message info';
    status.textContent = "⏳ Sending...";
    
    const cfid = "{{ profile.cfid }}";
    const data = {
    subject_line: subjectInput.value,
    message: messageInput.value
    };

    try {
    const res = await fetch(`/api/files/${cfid}/mail/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    const success = await res.text();
    
    if (success === "True") {
        status.className = 'status-message success';
        status.textContent = "✅ Email sent successfully!";
        form.reset();
        updateSubjectCount();
        updateMessageCount();
    } else {
        status.className = 'status-message error';
        status.textContent = "❌ Failed to send email. Please try again.";
    }
    } catch (err) {
    status.className = 'status-message error';
    status.textContent = "❌ Error sending email. Check your connection.";
    console.error(err);
    }
});