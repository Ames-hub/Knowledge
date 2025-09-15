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