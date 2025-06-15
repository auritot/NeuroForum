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
  const threadLinks = document.querySelectorAll(".chat-thread-link");
  const threadLink = document.querySelector(`.chat-thread-link[data-user="${fromUser}"]`);

  const chatSrc = chatFrame?.getAttribute("src") || "";
  const isChatVisible = !chatBox.classList.contains("d-none");
  const isChatOpen = isChatVisible && chatSrc.includes(`/chat/${fromUser}/`);

  // Clear all highlights
  threadLinks.forEach(el => el.classList.remove("active-thread"));

  // Highlight current thread if open
  if (isChatOpen && threadLink) {
    threadLink.classList.add("active-thread");
  }

  if (event.data.type === "new-message") {
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

document.querySelectorAll(".chat-thread-link").forEach(link => {
  link.addEventListener("click", (e) => {
    e.preventDefault();

    const username = link.dataset.user;
    const chatBox = document.getElementById("chat-box-floating");
    const chatFrame = document.getElementById("chat-frame");

    if (!username || !chatBox || !chatFrame) return;

    // Load the chat in iframe
    chatFrame.src = `/chat/${username}/?frame=1`;
    chatBox.classList.remove("d-none");

    // Visually mark active thread
    document.querySelectorAll(".chat-thread-link").forEach(el => el.classList.remove("active-thread"));
    link.classList.add("active-thread");

    // Remove notification highlight
    link.classList.remove("has-unread");
    const countSpan = link.querySelector(".unread-count");
    if (countSpan) {
      countSpan.textContent = "0";
      countSpan.classList.add("d-none");
    }
  });
});



