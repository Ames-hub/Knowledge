// export-pdf.js
document.addEventListener('DOMContentLoaded', function() {
    const exportBtn = document.getElementById('export-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', generatePDF);
    }
});

function generatePDF() {
    const exportBtn = document.getElementById('export-btn');
    const originalText = exportBtn.innerHTML;
    exportBtn.innerHTML = '<i>\u23f3</i> Generating PDF...';
    exportBtn.disabled = true;

    import('https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js')
        .then(() => import('https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.28/jspdf.plugin.autotable.min.js'))
        .then(() => createPDF())
        .catch(error => {
            console.error('Error loading PDF libraries:', error);
            alert('Error generating PDF. Please check your internet connection.');
        })
        .finally(() => {
            exportBtn.innerHTML = originalText;
            exportBtn.disabled = false;
        });
}

function createPDF() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });

    // Colors and layout
    const primary = [37, 99, 235];   // Deep blue
    const accent = [219, 234, 254];  // Soft blue
    const text = [31, 41, 55];       // Slate
    const muted = [107, 114, 128];   // Gray
    const light = [249, 250, 251];   // Light background
    const marginX = 15;
    let y = 20;

    // Header bar
    doc.setFillColor(...primary);
    doc.rect(0, 0, 210, 30, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(18);
    doc.text('Dianetics PC Folder Report', 105, 18, { align: 'center' });

    doc.setFontSize(9);
    doc.setFont('helvetica', 'normal');
    doc.text(`Generated on ${new Date().toLocaleDateString()}`, 105, 25, { align: 'center' });

    y = 40;

    // --- Profile Summary ---
    const profileName = document.querySelector('.profile-name')?.textContent.trim() || 'N/A';
    const profileOccupation = document.querySelector('.profile-occupation')?.textContent.trim() || 'N/A';
    const cfid = FileCFID || 'N/A';
    const age = document.querySelector('.meta-item:nth-child(2) span')?.textContent.replace('Age: ', '').trim() || 'N/A';
    const pronouns = document.querySelector('.meta-item:nth-child(3) span')?.textContent.replace('Pronouns: ', '').trim() || 'N/A';
    const isDianeticsPC = !!document.querySelector('.nav-link.active span')?.textContent.includes('PC Folder');

    doc.setFillColor(...accent);
    doc.roundedRect(marginX, y, 180, 25, 3, 3, 'F');
    doc.setTextColor(...text);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(14);
    doc.text(profileName, marginX + 10, y + 10);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10);
    doc.setTextColor(...muted);
    doc.text(profileOccupation, marginX + 10, y + 18);
    y += 35;

    // --- Personal Details ---
    addSectionHeader(doc, 'PERSONAL DETAILS', marginX, y);
    y += 10;

    const personalDetails = [
        ['Central File ID', cfid],
        ['Name', profileName],
        ['Age', age],
        ['Pronouns', pronouns],
        ['Occupation', profileOccupation],
        ['Dianetics PC', isDianeticsPC ? 'Yes' : 'No']
    ];

    doc.autoTable({
        startY: y,
        head: [['Field', 'Value']],
        body: personalDetails,
        theme: 'plain',
        headStyles: {
            fillColor: primary,
            textColor: 255,
            fontStyle: 'bold',
            halign: 'center'
        },
        styles: { fontSize: 10, cellPadding: 4, textColor: text },
        bodyStyles: { fillColor: light },
        alternateRowStyles: { fillColor: accent },
        margin: { left: marginX, right: marginX },
        tableLineColor: [221, 221, 221],
        tableLineWidth: 0.1
    });

    y = doc.lastAutoTable.finalY + 12;

    // --- Dianetics PC Profile ---
    if (isDianeticsPC) {
        addSectionHeader(doc, 'DIANETICS PC PROFILE', marginX, y);
        y += 10;

        const dianeticsFields = [
            ['Last Action', '#field-last_action'],
            ['Sonic Shut-off', '#field-sonic_shutoff'],
            ['Visio Shut-off', '#field-visio_shutoff'],
            ['Stuck On Time Track', '#field-stuck_case'],
            ['Latest Age Flash', '#field-stuck_age'],
            ['Control Circuits', '#field-control_case'],
            ['Dub-in Case', '#field-fabricator_case'],
            ['Estimated Tone Level', '#field-tone_level'],
            ['Actual Class of Mind', 'span:contains("Actual Class of Mind") + span'],
            ['Apparent Class of Mind', 'span:contains("Apparent Class of Mind") + span']
        ];

        const dianeticsData = dianeticsFields.map(([label, selector]) => {
            let el;
            if (selector.startsWith('#')) {
                el = document.querySelector(selector);
            } else {
                el = Array.from(document.querySelectorAll('.field')).find(f =>
                    f.querySelector('label')?.textContent.includes(label)
                )?.querySelector('span');
            }
            return [label, el ? el.textContent.trim() : 'N/A'];
        });

        doc.autoTable({
            startY: y,
            head: [['Field', 'Value']],
            body: dianeticsData,
            theme: 'plain',
            headStyles: { fillColor: primary, textColor: 255, fontStyle: 'bold', halign: 'center' },
            styles: { fontSize: 9, cellPadding: 3, textColor: text },
            bodyStyles: { fillColor: light },
            alternateRowStyles: { fillColor: accent },
            margin: { left: marginX, right: marginX }
        });

        y = doc.lastAutoTable.finalY + 12;
    }

    // --- Potential Value Estimation ---
    const potentialCard = document.querySelector('.card h3.card-title')?.textContent.includes('Potential Value Estimation');
    if (potentialCard) {
        addSectionHeader(doc, 'POTENTIAL VALUE ESTIMATION', marginX, y);
        y += 10;

        const canHandleLife = document.getElementById('field-can_handle_life')?.textContent.trim() || 'N/A';
        const thetaEndowment = document.getElementById('theta_display')?.textContent.trim() || 'N/A';

        const potentialData = [
            ['Can Handle Life', canHandleLife],
            ['Theta Endowment', thetaEndowment]
        ];

        doc.autoTable({
            startY: y,
            head: [['Field', 'Value']],
            body: potentialData,
            theme: 'plain',
            headStyles: { fillColor: primary, textColor: 255, fontStyle: 'bold', halign: 'center' },
            styles: { fontSize: 9, cellPadding: 3, textColor: text },
            bodyStyles: { fillColor: light },
            alternateRowStyles: { fillColor: accent },
            margin: { left: marginX, right: marginX }
        });

        y = doc.lastAutoTable.finalY + 12;
    }

    // --- Dynamics Strengths ---
    const dynamics = [
        ['Self', document.getElementById('dynamic-self')?.value || 'N/A'],
        ['Sex and Family', document.getElementById('dynamic-sex-family')?.value || 'N/A'],
        ['Groups', document.getElementById('dynamic-groups')?.value || 'N/A'],
        ['Mankind', document.getElementById('dynamic-mankind')?.value || 'N/A']
    ];

    addSectionHeader(doc, 'DYNAMIC STRENGTHS', marginX, y);
    y += 10;

    doc.autoTable({
        startY: y,
        head: [['Dynamic', 'Strength (0–3)']],
        body: dynamics,
        theme: 'plain',
        headStyles: { fillColor: primary, textColor: 255, fontStyle: 'bold', halign: 'center' },
        styles: { fontSize: 9, cellPadding: 3, textColor: text },
        bodyStyles: { fillColor: light },
        alternateRowStyles: { fillColor: accent },
        margin: { left: marginX, right: marginX }
    });

    // --- Footer ---
    const pages = doc.internal.getNumberOfPages();
    for (let i = 1; i <= pages; i++) {
        doc.setPage(i);
        doc.setFontSize(8);
        doc.setTextColor(...muted);
        doc.text(`Page ${i} of ${pages}`, 195, 290, { align: 'right' });
        doc.text('CONFIDENTIAL - FOR AUTHORIZED USE ONLY', 105, 290, { align: 'center' });
    }

    const fileName = `PC Folder - ${profileName}.pdf`;
    doc.save(fileName);
}

function addSectionHeader(doc, text, x, y) {
    doc.setFillColor(...[219, 234, 254]);
    doc.roundedRect(x, y, 180, 7, 2, 2, 'F');
    doc.setTextColor(...[31, 41, 55]);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(10);
    doc.text(text, x + 5, y + 5);
}
