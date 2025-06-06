// ContentFiltering.js

let filteredWords = [];

window.addEventListener('DOMContentLoaded', () => {
    const titleInput = document.getElementById('postTitle');
    const descInput = document.getElementById('postDescription');
    const submitBtn = document.querySelector("button[type='submit']");

    // Fetch filtered words from the backend API
    fetch('/api/filtered-words')
        .then(response => response.json())
        .then(data => {
            // Convert all words to lowercase for consistent comparison
            filteredWords = data.map(item => item.FilterContent.toLowerCase());
        })
        .catch(error => {
            console.error('Error fetching filtered words:', error);
        });

    function containsFilteredWords(text) {
        const content = text.toLowerCase();
        return filteredWords.some(word => content.includes(word));
    }

    function validateForm() {
        const titleHasBadWord = containsFilteredWords(titleInput.value);
        const descHasBadWord = containsFilteredWords(descInput.value);
        const hasBadWord = titleHasBadWord || descHasBadWord;

        // Add or remove red outline
        titleInput.classList.toggle('is-invalid', titleHasBadWord);
        descInput.classList.toggle('is-invalid', descHasBadWord);

        // Disable submit button if there's any invalid input
        submitBtn.disabled = hasBadWord;
    }

    // Listen for changes
    titleInput.addEventListener('input', validateForm);
    descInput.addEventListener('input', validateForm);
});
