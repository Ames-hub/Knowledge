const form = document.getElementById('expense-form');
const tableBody = document.getElementById('expense-table').querySelector('tbody');
const weeklyTargetSpan = document.getElementById('weekly-target');
const totalAnnualExpensesSpan = document.getElementById('total-annual-expenses');

let totalAnnualCost = 0;
let expensePieChart; // global for dynamic updates

form.addEventListener('submit', function(event) {
    event.preventDefault();

    const name = document.getElementById('expense-name').value;
    const amount = parseFloat(document.getElementById('expense-amount').value);
    const frequency = parseInt(document.getElementById('expense-frequency').value);

    if (name && !isNaN(amount) && !isNaN(frequency)) {
        let annualCost;
        if (frequency === 1) {
            annualCost = amount * 365;
        } else if (frequency === 7) {
            annualCost = amount * 52; // 52 weeks exactly
        } else if (frequency === 30 || frequency === 31) {
            annualCost = amount * 12;
        } else if (frequency === 365) {
            annualCost = amount;
        } else {
            // fallback for irregular intervals in days
            annualCost = (365 / frequency) * amount;
        }

        // Add the new expense's annual cost to the total
        totalAnnualCost += annualCost;

        const newRow = document.createElement('tr');
        newRow.setAttribute('data-annual-cost', annualCost);
        newRow.innerHTML = `
            <td>${name}</td>
            <td>$${amount.toFixed(2)}</td>
            <td>${frequency}</td>
            <td>$${annualCost.toFixed(2)}</td>
            <td><button class="remove-btn">Remove</button></td>
        `;
        tableBody.appendChild(newRow);

        updateTotals();

        // Send to backend
        fetch('/api/finances/fp/add_expense', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                amount: amount,
                frequency: frequency,
                annualCost: annualCost
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log('Expense saved:', data);
            loadExpenses(); // reload from backend to sync table & chart
        })
        .catch(error => {
            console.error('Error saving expense:', error);
        });

        form.reset();
    }
});

// Add a single event listener to the table body for efficiency
tableBody.addEventListener('click', function(event) {
    if (event.target.classList.contains('remove-btn')) {
        const row = event.target.closest('tr');
        const expenseName = row.querySelector('td').textContent; // first <td> is the name

        // Send DELETE request to backend
        fetch('/api/finances/fp/delete_expense', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name: expenseName })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log(`Expense "${expenseName}" deleted successfully`);
                // Remove row locally and reload chart/table
                loadExpenses();
            } else {
                console.error('Error deleting expense:', data.error);
            }
        })
        .catch(error => {
            console.error('Error deleting expense:', error);
        });
    }
});

function updateTotals() {
    const weeklyTarget = totalAnnualCost / 52;
    weeklyTargetSpan.textContent = `$${weeklyTarget.toFixed(2)}`;
    totalAnnualExpensesSpan.textContent = `$${totalAnnualCost.toFixed(2)}`;
}

function renderPieChart(expenses) {
    const labels = expenses.map(exp => exp.name);
    const data = expenses.map(exp => parseFloat(exp.amount));
    const backgroundColors = [
        '#3498db', '#2ecc71', '#e74c3c', '#f1c40f',
        '#9b59b6', '#1abc9c', '#e67e22', '#34495e'
    ];

    if (expensePieChart) {
        // Update existing chart
        expensePieChart.data.labels = labels;
        expensePieChart.data.datasets[0].data = data;
        expensePieChart.data.datasets[0].backgroundColor = backgroundColors.slice(0, labels.length);
        expensePieChart.update();
    } else {
        // Create new chart
        const ctx = document.getElementById('expense-pie-chart').getContext('2d');
        expensePieChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Expenses',
                    data: data,
                    backgroundColor: backgroundColors.slice(0, labels.length),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.label}: $${context.parsed}`;
                            }
                        }
                    }
                }
            }
        });
    }
}

async function loadExpenses() {
    try {
        const response = await fetch('/api/finances/fp/get_expenses');
        if (!response.ok) throw new Error('Failed to fetch expenses');

        const expenses = await response.json();

        totalAnnualCost = 0; // reset before reloading
        tableBody.innerHTML = ''; // clear current table

        expenses.forEach(expense => {
            const annualCost = parseFloat(expense.annual_cost);
            totalAnnualCost += annualCost;

            const newRow = document.createElement('tr');
            newRow.setAttribute('data-annual-cost', annualCost);
            newRow.innerHTML = `
                <td>${expense.name}</td>
                <td>$${parseFloat(expense.amount).toFixed(2)}</td>
                <td>${expense.frequency}</td>
                <td>$${annualCost.toFixed(2)}</td>
                <td><button class="remove-btn">Remove</button></td>
            `;
            tableBody.appendChild(newRow);
        });

        updateTotals();
        renderPieChart(expenses);
    } catch (err) {
        console.error('Error loading expenses:', err);
    }
}

document.addEventListener('DOMContentLoaded', loadExpenses);
