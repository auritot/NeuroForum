document.addEventListener("DOMContentLoaded", function () {
  const chatBtn    = document.getElementById("chat-btn");
  const chatBox    = document.getElementById("chat-box-floating");
  const chatFrame  = document.getElementById("chat-frame");
  const chatOverlay= document.getElementById("chat-overlay");
  const closeBtn   = document.getElementById("close-chat");
  const threadLinks= document.querySelectorAll(".chat-thread-link");

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

  // Toggle panel when you click the chat icon
  chatBtn.addEventListener("click", () => {
    openChat();
    // if we've never loaded anything (or we're on landing), default to landing
    if (!chatFrame.src || chatFrame.src.endsWith("landing/?frame=1")) {
      chatFrame.src = "/chat/landing/?frame=1";
    }
  });

  // Close panel on “X” or overlay click
  closeBtn.addEventListener("click",   closeChat);
  chatOverlay.addEventListener("click", closeChat);

  // Clicking an existing thread
  threadLinks.forEach((el) => {
    el.addEventListener("click", (e) => {
      e.preventDefault();
      const user = el.dataset.user;
      if (!user) return;
      chatFrame.src = `/chat/${user}/?frame=1`;
      threadLinks.forEach((l) => l.classList.remove("active-thread"));
      el.classList.add("active-thread");
      openChat();
    });
  });

  // ──────────────────────────────────────────────────────────
  // Hijack “Start New Chat” form so it loads in the iframe
  const sidebarForm = document.querySelector("#chat-sidebar form");
  if (sidebarForm) {
    sidebarForm.addEventListener("submit", function (e) {
      e.preventDefault();    // stop full-page navigation

      const input = document.getElementById("sidebarUsernameIframe");
      const user  = input.value.trim().toLowerCase();
      if (!user) return;     // nothing to do

      // Clear any prior active‐thread styling
      threadLinks.forEach((l) => l.classList.remove("active-thread"));

      // If they already chatted, highlight it
      const match = Array.from(threadLinks).find((l) => l.dataset.user === user);
      if (match) match.classList.add("active-thread");

      // Load that chat in the iframe
      chatFrame.src = `/chat/${user}/?frame=1`;

      // Open the panel
      openChat();
    });
  }

  // Once the iframe finishes loading, remove its spinner
  chatFrame.addEventListener("load", () => {
    chatFrame.classList.remove("loading");
    const m = chatFrame.src.match(/\/chat\/([^/]+)\//);
    if (m) {
      const active = m[1];
      threadLinks.forEach((el) =>
        el.classList.toggle("active-thread", el.dataset.user === active)
      );
    }
  });
});
