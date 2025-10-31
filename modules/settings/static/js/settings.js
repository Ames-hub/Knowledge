function saveConfig() {
	const config = {};
	// Grab all input/select elements inside config cards
	const inputs = document.querySelectorAll('#config-container .config-card input, #config-container .config-card select');

	inputs.forEach(input => {
		const name = input.dataset.configName;
		if (!name) return; // skip if no name
		let value;
		if (input.type === 'checkbox') {
			value = input.checked;
		} else if (input.type === 'number') {
			value = Number(input.value);
		} else {
			value = input.value;
		}
		config[name] = value;
	});

	// Send the config object to the server
	fetch('/api/settings/save', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({"config": config})
	})
	.then(res => res.text())
	.then(data => {
		console.log('Server response:', data);
		alert('Settings saved successfully!');
	})
	.catch(err => {
		console.error('Error saving settings:', err);
		alert('Failed to save settings. Check console.');
	});
}

function loadConfig() {
	fetch('/api/settings/load')
		.then(res => {
			if (!res.ok) throw new Error(`HTTP error ${res.status}`);
			return res.json();
		})
		.then(data => {
			const inputs = document.querySelectorAll('#config-container .config-card input, #config-container .config-card select');
			
			let weekdays_map = {
				1: "monday",
				2: "tuesday",
				3: "wednesday",
				4: "thursday",
				5: "friday",
				6: "saturday",
				7: "sunday"
			};
			
			// Convert from number to text
			data.weekday_end = weekdays_map[data.weekday_end]

			const config = data;

			inputs.forEach(input => {
				const name = input.dataset.configName;
				if (!name || !(name in config)) return;
				let value = config[name];
				
				if (input.type === 'checkbox') {
					input.checked = Boolean(value);
				} else {
					input.value = value;
				}
			});
		})
		.catch(err => {
			console.error('Error loading settings:', err);
			alert('Failed to load settings. Check console.');
		});
}

document.addEventListener('DOMContentLoaded', loadConfig);