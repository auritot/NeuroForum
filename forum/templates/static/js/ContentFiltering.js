let filteredWords = [];

window.addEventListener('DOMContentLoaded', () => {
    const submitButtons = document.querySelectorAll("button[type='submit'], .chat-send-button");
    const titleInput = document.getElementById('postTitle');
    const descInput = document.getElementById('postDescription');
    const commentInput = document.getElementById('commentText');
    const chatInput = document.getElementById('chat-input');
    const chatSidebarMain = document.getElementById('sidebarUsernameMain');
    const sidebarFindBtnMain = document.getElementById('sidebarFindBtnMain');
    const chatSidebarIframe = document.getElementById('sidebarUsernameIframe');
    const sidebarFindBtnIframe = document.getElementById('sidebarFindBtnIframe');
    const editInputs = document.querySelectorAll('.edit-comment-form textarea');

    const allFields = [titleInput, descInput, commentInput, chatInput, chatSidebarMain, sidebarFindBtnMain, chatSidebarIframe, sidebarFindBtnIframe, ...editInputs].filter(Boolean);

    fetch('/api/filtered-words/')
        .then(response => response.json())
        .then(data => {
            filteredWords = data.map(item => item.FilterContent.toLowerCase());
        })
        .catch(error => {
            console.error('Error fetching filtered words:', error);
        });

    function containsFilteredWords(text) {
        return filteredWords.some(word => text.toLowerCase().includes(word));
    }

    function containsInvalidSpecialChars(text) {
        // Only allow characters, numbers, and certain special characters .,!?()@
        const allowed = /^[a-zA-Z0-9 .,!?()@]*$/;
        return !allowed.test(text);
    }

    function validateField(input) {
        const value = input.value || "";
        const hasBadWord = containsFilteredWords(value);
        const hasSpecialChar = containsInvalidSpecialChars(value);
        const isInvalid = hasBadWord || hasSpecialChar;

        input.classList.toggle('is-invalid', isInvalid);
        return isInvalid;
    }

    function validateForm() {
        const anyInvalid = allFields.some(input => validateField(input));
        submitButtons.forEach(btn => btn.disabled = anyInvalid);
    }

    allFields.forEach(input => {
        input.addEventListener('input', validateForm);
    });

    // Sidebar MAIN validation
    if (chatSidebarMain && sidebarFindBtnMain) {
        chatSidebarMain.addEventListener('input', () => {
            const isInvalid = validateField(chatSidebarMain);
            sidebarFindBtnMain.disabled = isInvalid;
        });
        sidebarFindBtnMain.disabled = validateField(chatSidebarMain);
    }

    // Sidebar IFRAME validation
    if (chatSidebarIframe && sidebarFindBtnIframe) {
        chatSidebarIframe.addEventListener('input', () => {
            const isInvalid = validateField(chatSidebarIframe);
            sidebarFindBtnIframe.disabled = isInvalid;
        });
        sidebarFindBtnIframe.disabled = validateField(chatSidebarIframe);
    } 

    const chatForm = document.querySelector("#chat-form");
    if (chatForm && chatInput) {
        chatForm.addEventListener("submit", function (e) {
            if (validateField(chatInput)) {
                e.preventDefault(); // Prevent sending
            }
        });
    }
});
