document.getElementById('search-bar').addEventListener('input', function () {
    const query = this.value.toLowerCase();
    const topics = document.querySelectorAll('.topic');

    topics.forEach(topic => {
        let matches = false;

        topic.querySelectorAll('li').forEach(item => {
            const subtopicText = item.querySelector('a').innerText.toLowerCase();
            const descriptionText = item.querySelector('p').innerText.toLowerCase();

            if (subtopicText.includes(query) || descriptionText.includes(query)) {
                item.style.display = 'block';
                matches = true;
            } else {
                item.style.display = 'none';
            }
        });

        topic.style.display = matches ? 'block' : 'none';
    });
});
