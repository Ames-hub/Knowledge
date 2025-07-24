function filterNames() {
    const filter = document.getElementById('search-input').value.toLowerCase();
    const list = document.getElementById('people-list');
    const items = list.getElementsByTagName('a');

    for (let i = 0; i < items.length; i++) {
        const name = items[i].textContent.toLowerCase();
        if (name.includes(filter)) {
            items[i].style.display = '';
        } else {
            items[i].style.display = 'none';
        }
    }
}