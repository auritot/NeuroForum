document.addEventListener("DOMContentLoaded", function () {
    const placeholder = document.getElementById("commentPlaceholder");
    const formContainer = document.getElementById("commentFormContainer");
    const cancelBtn = document.getElementById("cancelComment");
    const textarea = formContainer.querySelector('textarea');

    if (placeholder && formContainer && cancelBtn) {
        placeholder.addEventListener("click", () => {
            placeholder.classList.add("d-none");
            formContainer.classList.remove("d-none");
            document.getElementById("commentText").focus();
        });

        cancelBtn.addEventListener("click", () => {
            formContainer.classList.add("d-none");
            placeholder.classList.remove("d-none");
            document.getElementById("commentText").value = "";
            textarea.style.height = "auto";
        });
    }
});

document.addEventListener("input", function (e) {
    if (e.target.tagName.toLowerCase() === "textarea" && e.target.classList.contains("auto-expand")) {
        e.target.style.height = "auto"; // Reset height
        e.target.style.height = (e.target.scrollHeight) + "px"; // Set new height
    }
});

document.addEventListener('DOMContentLoaded', function () {
    // Toggle the edit form when clicking "Edit"
    document.querySelectorAll('.edit-comment-btn').forEach(function (editBtn) {
        editBtn.addEventListener('click', function (e) {
            e.preventDefault();

            const cardBody = editBtn.closest('.card-body');
            const commentText = cardBody.querySelector('.comment-content');
            const editForm = cardBody.querySelector('.edit-comment-form');
            const textarea = editForm.querySelector('textarea');

            if (commentText && editForm && textarea) {
                // Fill textarea with current comment content
                textarea.value = commentText.textContent.trim();

                // Show form, hide comment display
                commentText.classList.add('d-none');
                editForm.classList.remove('d-none');

                // Optional: auto-expand
                textarea.style.height = "auto";
                textarea.style.height = (textarea.scrollHeight) + "px";
            }
        });
    });

    // Cancel the edit form
    document.querySelectorAll('.cancel-edit').forEach(function (cancelBtn) {
        cancelBtn.addEventListener('click', function () {
            const form = cancelBtn.closest('.edit-comment-form');
            const cardBody = form.closest('.card-body');
            const commentText = cardBody.querySelector('.comment-content');

            if (form && commentText) {
                form.classList.add('d-none');
                commentText.classList.remove('d-none');
            }
        });
    });
});