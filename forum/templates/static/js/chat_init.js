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

      // Reset notification class when opening
      chatBtn.classList.remove("has-notification");
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
    const chatBtn = document.getElementById("chat-btn");
    const chatFrame = document.getElementById("chat-frame");

    if (chatBtn && chatFrame) {
      const isChatOpen = !chatFrame.classList.contains("loading") && !chatBox.classList.contains("d-none");

      // Global badge logic: if chat box isn't open, show the glow
      if (!isChatOpen) {
        console.log("🔔 Showing global chat notification");
        chatBtn.classList.add("has-notification");
      }
    }
  }
});
