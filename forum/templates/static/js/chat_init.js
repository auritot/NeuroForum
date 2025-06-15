document.addEventListener("DOMContentLoaded", function () {
  const chatBtn = document.getElementById("chat-btn");
  const chatBox = document.getElementById("chat-box");
  const chatFrame = document.getElementById("chat-frame");
  const chatOverlay = document.getElementById("chat-overlay");
  const closeBtn = document.getElementById("close-chat");
  const threadLinks = document.querySelectorAll(".chat-thread-link");

  if (!chatBtn || !chatBox || !chatFrame || !closeBtn || !chatOverlay) return;

  function openChat() {
    chatBox.classList.add("open");
    chatOverlay.classList.add("show");
  }

  function closeChat() {
    chatBox.classList.remove("open");
    chatOverlay.classList.remove("show");
    chatFrame.src = "";
    threadLinks.forEach((el) => el.classList.remove("active-thread"));
  }

  chatBtn.addEventListener("click", function () {
    openChat();
    if (chatFrame.src === "" || chatFrame.src.endsWith("landing/?frame=1")) {
      chatFrame.src = "/chat/landing/?frame=1";
    }
  });

  closeBtn.addEventListener("click", closeChat);
  chatOverlay.addEventListener("click", closeChat);

  threadLinks.forEach((el) => {
    el.addEventListener("click", function (e) {
      e.preventDefault();
      const user = el.dataset.user;
      if (user) {
        chatFrame.src = `/chat/${user}/?frame=1`;
        threadLinks.forEach((link) => link.classList.remove("active-thread"));
        el.classList.add("active-thread");
        el.classList.remove("has-unread");
        const countSpan = el.querySelector(".unread-count");
        if (countSpan) {
          countSpan.textContent = "0";
          countSpan.classList.add("d-none");
        }
        chatBtn.classList.remove("has-notification");
        openChat();
      }
    });
  });

  window.addEventListener("message", function (event) {
    if (event.data.type === "new-message") {
      const fromUser = event.data.from;
      const threadLink = document.querySelector(`.chat-thread-link[data-user="${fromUser}"]`);
      const isChatOpen = chatBox.classList.contains("open") && chatFrame.src.includes(`/chat/${fromUser}/`);

      if (threadLink) {
        if (!isChatOpen) {
          const countSpan = threadLink.querySelector(".unread-count");
          let count = parseInt(countSpan?.textContent || "0", 10) + 1;
          countSpan.textContent = count;
          countSpan.classList.remove("d-none");
          threadLink.classList.add("has-unread");
          chatBtn.classList.add("has-notification");
        } else {
          threadLink.classList.add("active-thread");
        }
      }
    }

    if (event.data.type === "chat-read") {
      const fromUser = event.data.from;
      threadLinks.forEach(el => {
        if (el.dataset.user === fromUser) {
          el.classList.remove("has-unread");
          el.classList.add("active-thread");
          const countSpan = el.querySelector(".unread-count");
          if (countSpan) {
            countSpan.textContent = "0";
            countSpan.classList.add("d-none");
          }
        }
      });
      chatBtn.classList.remove("has-notification");
    }
  });

  chatFrame?.addEventListener("load", () => {
    chatFrame.classList.remove("loading");
    const src = chatFrame.src;
    const userMatch = src.match(/\/chat\/([^/]+)\//);
    if (userMatch) {
      const activeUser = userMatch[1];
      document.querySelectorAll(".chat-thread-link").forEach(el => {
        el.classList.toggle("active-thread", el.dataset.user === activeUser);
      });
    }
  });
});
