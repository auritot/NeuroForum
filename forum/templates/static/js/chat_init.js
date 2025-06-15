// static/js/chat_init.js

document.addEventListener("DOMContentLoaded", () => {
  const chatBtn     = document.getElementById("chat-btn");
  const chatBox     = document.getElementById("chat-box-floating");
  const closeBtn    = document.getElementById("close-chat");
  const chatFrame   = document.getElementById("chat-frame");
  const threadLinks = Array.from(document.querySelectorAll(".chat-thread-link"));

  function openChat() {
    chatBox.classList.remove("d-none");
  }
  function closeChat() {
    chatBox.classList.add("d-none");
    chatFrame.src = "";
    threadLinks.forEach(l => l.classList.remove("active-thread"));
  }

  chatBtn.addEventListener("click", () => {
    openChat();
    if (!chatFrame.src.includes("/chat/")) {
      chatFrame.src = "/chat/landing/?frame=1";
    }
    chatBtn.classList.remove("has-notification");
  });
  closeBtn.addEventListener("click", closeChat);

  // click on a thread in the sidebar
  threadLinks.forEach(link => {
    link.addEventListener("click", e => {
      e.preventDefault();
      const user = link.dataset.user;
      if (!user) return;
      chatFrame.src = `/chat/${user}/?frame=1`;
      threadLinks.forEach(l => l.classList.remove("active-thread"));
      link.classList.add("active-thread");
      // clear that thread’s unread badge
      const badge = link.querySelector(".unread-count");
      if (badge) {
        badge.textContent = "0";
        badge.classList.add("d-none");
      }
      chatBtn.classList.remove("has-notification");
      openChat();
    });
  });

  // receive “new-message” from inner frames (either a real message or an unread ping)
  window.addEventListener("message", event => {
    if (event.data.type !== "new-message") return;
    const fromUser = (event.data.from || "").toLowerCase();
    const threadLink = document.querySelector(`.chat-thread-link[data-user="${fromUser}"]`);
    const isOpen     = !chatBox.classList.contains("d-none") && chatFrame.src.includes(`/chat/${fromUser}/`);

    if (threadLink) {
      if (!isOpen) {
        // bump unread‐badge
        const badge = threadLink.querySelector(".unread-count");
        let count   = parseInt(badge?.textContent || "0", 10) + 1;
        badge.textContent = count;
        badge.classList.remove("d-none");
        threadLink.classList.add("has-unread");
        // glow the chat icon
        chatBtn.classList.add("has-notification");
      } else {
        // if that thread is open, highlight it
        threadLink.classList.add("active-thread");
      }
    } else {
      // brand‐new partner: glow the chat icon too
      chatBtn.classList.add("has-notification");
    }
  });
});
