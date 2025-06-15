// static/js/chat_init.js

document.addEventListener("DOMContentLoaded", function () {
  const chatBtn    = document.getElementById("chat-btn");
  const chatBox    = document.getElementById("chat-box-floating");
  const closeChat  = document.getElementById("close-chat");
  const chatFrame  = document.getElementById("chat-frame");
  const threadLinks = document.querySelectorAll(".chat-thread-link");

  if (!chatBtn) return;

  // 1) Open chat panel
  chatBtn.addEventListener("click", () => {
    chatBox.classList.remove("d-none");
    // if no thread selected yet, landing page
    if (!chatFrame.src || chatFrame.src.includes("landing")) {
      chatFrame.src = "/chat/landing/?frame=1";
    }
    // clear bell glow
    chatBtn.classList.remove("has-notification");
  });

  // 2) Close button
  closeChat?.addEventListener("click", () => {
    chatBox.classList.add("d-none");
    chatFrame.src = "";
    threadLinks.forEach(el => el.classList.remove("active-thread"));
  });

  // 3) When iframe loads, un-hide content
  chatFrame?.addEventListener("load", () => {
    chatFrame.classList.remove("loading");
  });

  // 4) Thread click (open that user’s chat)
  threadLinks.forEach(link => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const user = link.dataset.user;
      if (!user) return;
      chatFrame.src = `/chat/${user}/?frame=1`;
      threadLinks.forEach(el => el.classList.remove("active-thread"));
      link.classList.add("active-thread");
      link.classList.remove("has-unread");
      const countSpan = link.querySelector(".unread-count");
      if (countSpan) {
        countSpan.textContent = "0";
        countSpan.classList.add("d-none");
      }
      chatBtn.classList.remove("has-notification");
      chatBox.classList.remove("d-none");
    });
  });

  // 5) Listen for child-postMessages
  window.addEventListener("message", (event) => {
    const { type, from } = event.data || {};

    if (type === "new-message" && from) {
      const threadLink = document.querySelector(`.chat-thread-link[data-user="${from}"]`);
      const isOpen = !chatBox.classList.contains("d-none") 
                     && chatFrame.src.includes(`/chat/${from}/`);

      if (threadLink) {
        if (!isOpen) {
          // bump unread badge
          const countSpan = threadLink.querySelector(".unread-count");
          let count = parseInt(countSpan?.textContent || "0", 10) + 1;
          countSpan.textContent = count;
          countSpan.classList.remove("d-none");
          threadLink.classList.add("has-unread");
          // glow the main chat icon
          chatBtn.classList.add("has-notification");
        } else {
          // if this thread is open, highlight it
          threadLink.classList.add("active-thread");
        }
      } else {
        // global chat icon if message from a **new** partner
        chatBtn.classList.add("has-notification");
      }
    }

    if (type === "chat-read" && from) {
      // clear the clicked partner’s unread
      threadLinks.forEach(el => {
        if (el.dataset.user === from) {
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
});
