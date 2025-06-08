document.addEventListener("DOMContentLoaded", function () {
    const chatBtn = document.getElementById("chat-btn");
    const chatBox = document.getElementById("chat-box-floating");
    const closeChat = document.getElementById("close-chat");
    const chatFrame = document.getElementById("chat-frame");

    if (chatBtn) {
        chatBtn.addEventListener("click", () => {
                if (username) {
                    chatFrame.src = "{% url 'chat_landing' %}?frame=1";
                    chatBox.classList.remove("d-none");
                } else {
                    alert("Please log in to use chat.");
                }

        });
    }

    closeChat.addEventListener("click", () => {
        chatBox.classList.add("d-none");
        chatFrame.src = "";
    });

    chatFrame.addEventListener("load", () => {
        chatFrame.classList.remove("loading");
    });

});