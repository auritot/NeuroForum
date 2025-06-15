document.addEventListener("DOMContentLoaded", function () {
  const chatBtn = document.getElementById("chat-btn");
  const chatBox = document.getElementById("chat-box-floating");
  const closeChat = document.getElementById("close-chat");
  const chatFrame = document.getElementById("chat-frame");

  const username = chatBtn?.dataset.username || null;

  if (chatBtn) {
    chatBtn.addEventListener("click", () => {
      if (username) {
        chatFrame.src = "/chat/landing/?frame=1";
        chatBox.classList.remove("d-none");
      } else {
        alert("Please log in to use chat.");
      }
    });
  }

  closeChat?.addEventListener("click", () => {
    chatBox.classList.add("d-none");
    chatFrame.src = "";
  });

  chatFrame?.addEventListener("load", () => {
    chatFrame.classList.remove("loading");
  });
});

window.addEventListener("message", (event) => {
  if (event.data?.type === "new-message") {
    const fromUser = event.data.from;

    // Only notify if the chat iframe is not focused on that user
    const isAlreadyChatting = chatFrame.src.includes(`/chat/${fromUser}/`);
    if (!isAlreadyChatting) {
      const chatBtn = document.getElementById("chat-btn");
      if (chatBtn) {
        chatBtn.src = "/static/icons/notification_icon.png"; // Replace with actual path
        chatBtn.classList.add("has-notification");
      }
    }
  }
});

chatBtn.addEventListener("click", () => {
  chatFrame.src = "/chat/landing/?frame=1";
  chatBox.classList.remove("d-none");

  // Reset chat icon
  chatBtn.src = "/static/icons/chat.png"; // back to default
  chatBtn.classList.remove("has-notification");
});
