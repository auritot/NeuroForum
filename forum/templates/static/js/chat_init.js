document.addEventListener("DOMContentLoaded", () => {
  // 1) Back-to-Chats button
  const backBtn = document.getElementById("back-to-chats-btn");
  if (backBtn) {
    backBtn.addEventListener("click", e => {
      e.preventDefault();
      window.parent.postMessage("back-to-chats", window.location.origin);
    });
  }

  // 2) Grab the chat UI elements
  const chatBtn     = document.getElementById("chat-btn");
  const chatBox     = document.getElementById("chat-box-floating");
  const chatFrame   = document.getElementById("chat-frame");
  const closeBtn    = document.getElementById("close-chat");
  const chatOverlay = document.getElementById("chat-overlay");
  const threadLinks = Array.from(document.querySelectorAll(".chat-thread-link"));
  const searchInput = document.getElementById("sidebarUsernameIframe");
  if (!chatBtn || !chatBox || !chatFrame || !closeBtn || !chatOverlay) return;

  function openChat() {
    chatBox.classList.remove("d-none");
    chatOverlay.classList.add("show");
  }
  function closeChat() {
    chatBox.classList.add("d-none");
    chatOverlay.classList.remove("show");
    chatFrame.src = "";
    threadLinks.forEach(a => a.classList.remove("active-thread"));
  }

  // 3) Toggling the overlay
  chatBtn.addEventListener("click", () => {
    openChat();
    if (!chatFrame.src || chatFrame.src.endsWith("landing/?frame=1")) {
      chatFrame.src = "/chat/landing/?frame=1";
      // auto-open first partner if you want:
      if (threadLinks.length) threadLinks[0].click();
    }
  });
  closeBtn.addEventListener("click", closeChat);
  chatOverlay.addEventListener("click", closeChat);

  // 4) **Clicking a thread** — **toggle on the <a>**, not the li
  threadLinks.forEach(link => {
    link.addEventListener("click", e => {
      e.preventDefault();
      const user = link.dataset.user;
      if (!user) return;

      // clear _all_ links, then highlight this one
      threadLinks.forEach(a => a.classList.remove("active-thread"));
      link.classList.add("active-thread");

      chatFrame.src = `/chat/${user}/?frame=1`;
      if (searchInput) searchInput.value = "";
      openChat();
    });
  });

  // 5) **When the iframe reloads** — skip landing page
  chatFrame.addEventListener("load", () => {
    chatFrame.classList.remove("loading");
    const url = chatFrame.src;
    if (url.endsWith("landing/?frame=1")) {
      // do nothing — preserve last highlight
      return;
    }
    const m = url.match(/\/chat\/([^/]+)\//);
    if (m) {
      const active = m[1];
      threadLinks.forEach(a =>
        a.classList.toggle("active-thread", a.dataset.user === active)
      );
    }
    if (searchInput) searchInput.value = "";
  });

  // 6) **Handle postMessage** — don’t clear highlights on back-to-chats
  window.addEventListener("message", e => {
    if (e.data === "close-chat") {
      closeChat();
    }
    else if (e.data === "back-to-chats") {
      chatFrame.src = "/chat/landing/?frame=1";
      // ← no more `threadLinks.forEach(...)` here!
    }
  });
});
