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

    // Color palette & layout
    const primary = [37, 99, 235];   // Deep blue
    const accent = [219, 234, 254];  // Soft blue
    const text = [31, 41, 55];       // Slate
    const muted = [107, 114, 128];   // Subtle gray
    const light = [249, 250, 251];   // Very light background
    const marginX = 15;
    let y = 20;

    // Header
    doc.setFillColor(...primary);
    doc.rect(0, 0, 210, 30, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(18);
    doc.text('Central Files Report', 105, 18, { align: 'center' });

    doc.setFontSize(9);
    doc.setFont('helvetica', 'normal');
    doc.text(`Generated on ${new Date().toLocaleDateString()}`, 105, 25, { align: 'center' });

    y = 40;

    // Profile summary card
    const profileName = document.querySelector('.profile-name').textContent.trim();
    const profileOccupation = document.querySelector('.profile-occupation').textContent.trim();
    const age = document.getElementById('field-age').textContent.trim();
    const pronouns = document.getElementById('field-pronouns').textContent.trim();
    const isDianeticsPC = document.getElementById('field-is_dianetics').textContent.trim();
    const occupation = document.getElementById('field-occupation').textContent.trim();

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

    // Personal Details
    addSectionHeader(doc, 'PERSONAL DETAILS', marginX, y);
    y += 10;

    const personalDetails = [
        ['Central File ID', FileCFID],
        ['Name', profileName],
        ['Age', age],
        ['Pronouns', pronouns],
        ['Occupation', occupation],
        ['Dianetics PC', isDianeticsPC]
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

    // Dianetics PC Profile
    if (isDianeticsPC.toLowerCase() === 'true' || isDianeticsPC === 'Yes') {
        addSectionHeader(doc, 'DIANETICS PC PROFILE', marginX, y);
        y += 10;

        const dianeticsFields = [
            'Last Action', 'Sonic Shut-off', 'Visio Shut-off', 
            'Stuck On Time Track', 'Latest Age Flash', 'Control Circuits',
            'Dub-in Case', 'Estimated Tone Level', 'Actual Class of Mind',
            'Apparent Class of Mind'
        ];

        const dianeticsData = dianeticsFields.map(field => {
            const element = document.querySelector(`[id*="${field.toLowerCase().replace(/ /g, '_')}"]`);
            return [field, element ? element.textContent.trim() : 'N/A'];
        });

        doc.autoTable({
            startY: y,
            head: [['Field', 'Value']],
            body: dianeticsData,
            theme: 'plain',
            headStyles: {
                fillColor: primary,
                textColor: 255,
                fontStyle: 'bold',
                halign: 'center'
            },
            styles: { fontSize: 9, cellPadding: 3, textColor: text },
            bodyStyles: { fillColor: light },
            alternateRowStyles: { fillColor: accent },
            margin: { left: marginX, right: marginX }
        });

        y = doc.lastAutoTable.finalY + 12;
    }

    // Invoices
    const invoicesTable = document.querySelector('.invoices-table');
    if (invoicesTable) {
        addSectionHeader(doc, 'ASSOCIATED INVOICES', marginX, y);
        y += 10;

        const rows = invoicesTable.querySelectorAll('tbody tr');
        const invoiceData = Array.from(rows).map(row => {
            const cells = row.querySelectorAll('td');
            const status = cells[3].querySelector('.status-badge');
            return [
                cells[0].textContent.trim(),
                cells[1].textContent.trim(),
                cells[2].textContent.trim(),
                status ? status.textContent.trim() : cells[3].textContent.trim()
            ];
        });

        if (invoiceData.length > 0) {
            doc.autoTable({
                startY: y,
                head: [['Invoice ID', 'Date', 'Amount', 'Status']],
                body: invoiceData,
                theme: 'striped',
                headStyles: {
                    fillColor: primary,
                    textColor: 255,
                    fontStyle: 'bold'
                },
                styles: { fontSize: 9, cellPadding: 3, textColor: text },
                alternateRowStyles: { fillColor: accent },
                margin: { left: marginX, right: marginX },
                columnStyles: { 3: { halign: 'center', cellWidth: 25 } }
            });
            y = doc.lastAutoTable.finalY + 12;
        }
    }

    // Debts
    const debtsTable = document.querySelector('.debts-table');
    if (debtsTable) {
        addSectionHeader(doc, 'ASSOCIATED DEBTS', marginX, y);
        y += 10;

        const rows = debtsTable.querySelectorAll('tbody tr');
        const debtData = Array.from(rows).map(row => {
            const cells = row.querySelectorAll('td');
            return Array.from(cells).map(c => c.textContent.trim());
        });

        if (debtData.length > 0) {
            doc.autoTable({
                startY: y,
                head: [['Debt ID', 'Debtor', 'Debtee', 'Amount', 'Start Date', 'End Date']],
                body: debtData,
                theme: 'striped',
                headStyles: { fillColor: primary, textColor: 255, fontStyle: 'bold' },
                styles: { fontSize: 8, cellPadding: 2, textColor: text },
                alternateRowStyles: { fillColor: accent },
                margin: { left: marginX, right: marginX }
            });
            y = doc.lastAutoTable.finalY + 12;
        }
    }

    // Notes
    const notesList = document.getElementById('notes-list');
    if (notesList) {
        const noteEntries = notesList.querySelectorAll('.note-entry');
        if (noteEntries.length > 0) {
            addSectionHeader(doc, 'PROFILE NOTES', marginX, y);
            y += 10;

            noteEntries.forEach((noteElement, i) => {
                const meta = noteElement.querySelector('.meta');
                const content = noteElement.querySelector('.note-content');
                if (!content) return;

                const metaText = meta ? meta.textContent.trim().replace(/\s+/g, ' ') : '';
                const contentText = content.textContent.trim();

                if (!contentText) return;

                // Start new page if needed
                if (y > 250) {
                    doc.addPage();
                    y = 20;
                }

                // Note header bar
                doc.setFillColor(...accent);
                doc.roundedRect(marginX, y, 180, 8, 2, 2, 'F');
                doc.setFont('helvetica', 'bold');
                doc.setFontSize(8);
                doc.setTextColor(...muted);
                doc.text(`Note ${i + 1}${metaText ? ' – ' + metaText : ''}`, marginX + 5, y + 5);
                y += 12;

                // Wrap note text
                const lines = doc.splitTextToSize(contentText, 175);
                const neededSpace = lines.length * 4 + 6;
                if (y + neededSpace > 280) {
                    doc.addPage();
                    y = 20;
                }

                doc.setFont('helvetica', 'normal');
                doc.setFontSize(9);
                doc.setTextColor(...text);
                doc.text(lines, marginX + 5, y);
                y += neededSpace;
            });
        }
    }

    // Footer: page numbers and confidentiality notice
    const pages = doc.internal.getNumberOfPages();
    for (let i = 1; i <= pages; i++) {
        doc.setPage(i);
        doc.setFontSize(8);
        doc.setTextColor(...muted);
        doc.text(`Page ${i} of ${pages}`, 195, 290, { align: 'right' });
        doc.text('CONFIDENTIAL - FOR AUTHORIZED USE ONLY', 105, 290, { align: 'center' });
    }

    const fileName = `Profile of ${profileName}.pdf`;
    doc.save(fileName);
}

function addSectionHeader(doc, text, x, y) {
    doc.setFillColor(37, 99, 235);
    doc.roundedRect(x, y, 180, 7, 2, 2, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(10);
    doc.text(text, x + 5, y + 5);
}
