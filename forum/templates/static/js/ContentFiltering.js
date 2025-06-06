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

    function containsInvalidSpecialChars(text) {
        // Allow letters, numbers, spaces, and these symbols: . , ! ( ) @ ?
        const allowed = /^[a-zA-Z0-9 .,!?()@]*$/;
        return !allowed.test(text);
    }

    function validateForm() {
        const title = titleInput.value;
        const desc = descInput.value;

        const titleHasBadWord = containsFilteredWords(title);
        const descHasBadWord = containsFilteredWords(desc);

        const titleHasSpecialChar = containsInvalidSpecialChars(title);
        const descHasSpecialChar = containsInvalidSpecialChars(desc);

        const isInvalid = titleHasBadWord || descHasBadWord || titleHasSpecialChar || descHasSpecialChar;

        titleInput.classList.toggle('is-invalid', titleHasBadWord || titleHasSpecialChar);
        descInput.classList.toggle('is-invalid', descHasBadWord || descHasSpecialChar);

        submitBtn.disabled = isInvalid;
    }

    // Listen for changes
    titleInput.addEventListener('input', validateForm);
    descInput.addEventListener('input', validateForm);
});
