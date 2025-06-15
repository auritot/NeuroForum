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
  if (!event.data?.type || !event.data?.from) return;

  const fromUser = event.data.from.toLowerCase();
  const chatBtn = document.getElementById("chat-btn");
  const chatFrame = document.getElementById("chat-frame");
  const chatBox = document.getElementById("chat-box-floating");
  const threadLink = document.querySelector(`.chat-thread-link[data-user="${fromUser}"]`);

  const chatSrc = chatFrame?.getAttribute("src") || "";
  const isChatLoaded = chatSrc !== "";
  const isChatVisible = !chatBox.classList.contains("d-none");
  const isChatOpen = isChatVisible && chatSrc.includes(`/chat/${fromUser}/`);


  if (event.data.type === "new-message") {
    // Only increase count if not already chatting with them
    if (!isChatOpen && threadLink) {
      const countSpan = threadLink.querySelector(".unread-count");
      let count = parseInt(countSpan.textContent || "0", 10) + 1;
      countSpan.textContent = count;
      countSpan.classList.remove("d-none");
      threadLink.classList.add("has-unread");
      chatBtn.classList.add("has-notification");
    }
  }

  if (event.data.type === "chat-read") {

    if (threadLink) {
      const countSpan = threadLink.querySelector(".unread-count");
      countSpan.textContent = "0";
      countSpan.classList.add("d-none");
      threadLink.classList.remove("has-unread");
    }

    chatBtn.classList.remove("has-notification");
  }
});


