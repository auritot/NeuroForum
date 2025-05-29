document.addEventListener("DOMContentLoaded", function () {
    const placeholder = document.getElementById("commentPlaceholder");
    const formContainer = document.getElementById("commentFormContainer");
    const cancelBtn = document.getElementById("cancelComment");

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
        });
    }
});

document.addEventListener("input", function (e) {
    if (e.target.tagName.toLowerCase() === "textarea" && e.target.classList.contains("auto-expand")) {
        e.target.style.height = "auto"; // Reset height
        e.target.style.height = (e.target.scrollHeight) + "px"; // Set new height
    }
});
