document.addEventListener("DOMContentLoaded", function () {
  const chatBtn = document.getElementById("chat-btn");
  const chatBox = document.getElementById("chat-box-floating");
  const chatFrame = document.getElementById("chat-frame");
  const chatOverlay = document.getElementById("chat-overlay");
  const closeBtn = document.getElementById("close-chat");
  const threadLinks = document.querySelectorAll(".chat-thread-link");

  if (!chatBtn || !chatBox || !chatFrame || !closeBtn || !chatOverlay) return;

  function openChat() {
    chatBox.classList.add("open");
    chatBox.classList.remove("d-none");
    chatOverlay.classList.add("show");
  }

  function closeChat() {
    chatBox.classList.remove("open");
    chatBox.classList.add("d-none");
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

    // hijack the “Start New Chat” form so it loads inside the iframe
  const sidebarForm = document.querySelector("#chat-sidebar form");
  if (sidebarForm) {
    sidebarForm.addEventListener("submit", function (e) {
      e.preventDefault();    // stop full-page navigation

      // grab & normalize the username
      const input = document.getElementById("sidebarUsernameIframe");
      const user  = input.value.trim().toLowerCase();
      if (!user) return;

      // clear any previously-active thread styling
      threadLinks.forEach((l) => l.classList.remove("active-thread"));

      // if that user already exists in the list, mark it active
      const match = Array.from(threadLinks).find((l) => l.dataset.user === user);
      if (match) match.classList.add("active-thread");

      // point the iframe at the new chat
      chatFrame.src = `/chat/${user}/?frame=1`;

      // open the panel (just like a thread-link click does)
      openChat();
    });
  }

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
