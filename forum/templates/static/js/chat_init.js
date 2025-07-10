document.addEventListener("DOMContentLoaded", () => {
  // 1) Bind the "Back to Chats" button first, before any bail-out checks:
  const backBtn = document.getElementById("back-to-chats-btn");
  if (backBtn) {
    backBtn.addEventListener("click", e => {
      e.preventDefault();
      window.parent.postMessage("back-to-chats", window.location.origin);
    });
  }

  const chatBtn     = document.getElementById("chat-btn");
  const chatBox     = document.getElementById("chat-box-floating");
  const chatFrame   = document.getElementById("chat-frame");
  const closeBtn    = document.getElementById("close-chat");
  const chatOverlay = document.getElementById("chat-overlay");
  const threadLinks = Array.from(document.querySelectorAll(".chat-thread-link"));
  const searchInput = document.getElementById("sidebarUsernameIframe");

  // if any of these are missing, bail out
  if (!chatBtn || !chatBox || !chatFrame || !closeBtn || !chatOverlay) return;

  function openChat() {
    chatBox.classList.remove("d-none");
    chatOverlay.classList.add("show");
  }

  function closeChat() {
    chatBox.classList.add("d-none");
    chatOverlay.classList.remove("show");
    chatFrame.src = "";
    threadLinks.forEach(el => el.classList.remove("active-thread"));
  }

  // toggle open/landing
  chatBtn.addEventListener("click", () => {
    openChat();
    if (!chatFrame.src || chatFrame.src.endsWith("landing/?frame=1")) {
      chatFrame.src = "/chat/landing/?frame=1";
      // then auto-click the first thread (if any)
      if (threadLinks.length) {
        threadLinks[0].click();
      }
    }
  });

  closeBtn.addEventListener("click", closeChat);
  chatOverlay.addEventListener("click", closeChat);

  // clicking an existing thread
  threadLinks.forEach(el => {
    el.addEventListener("click", e => {
      e.preventDefault();
      const user = el.dataset.user;
      if (!user) return;

      // Clear every link…
      threadLinks.forEach(a => a.classList.remove("active-thread"));
      // …then highlight this one
      el.classList.add("active-thread");

      chatFrame.src = `/chat/${user}/?frame=1`;
      openChat();
    });
  });

  // hijack “Start New Chat” form
  const sidebarForm = document.querySelector("#chat-sidebar form");
  if (sidebarForm) {
    sidebarForm.addEventListener("submit", e => {
      e.preventDefault();
      const input = document.getElementById("sidebarUsernameIframe");
      const user  = input.value.trim().toLowerCase();
      if (!user) return;
      // threadLinks.forEach(l => l.classList.remove("active-thread"));
      // const match = threadLinks.find(l => l.dataset.user === user);
      // if (match) match.classList.add("active-thread");
      const match = threadLinks.find(l => l.dataset.user === user);
      if (match) {
        threadLinks.forEach(l => l.classList.remove("active-thread"));
        match.classList.add("active-thread");
      }
      chatFrame.src = `/chat/${user}/?frame=1`;

      // clear your “find user” box
      if (searchInput) searchInput.value = "";

      openChat();
    });
  }

  // keep the little “active” highlight in sync when the iframe reloads
  chatFrame.addEventListener("load", () => {
    const m = chatFrame.src.match(/\/chat\/([^/]+)\//);
    if (m) {
      const active = m[1];
      threadLinks.forEach(el =>
        el.classList.toggle("active-thread", el.dataset.user === active)
      );
    }
  });


  window.addEventListener('message', e => {
    const allowedOrigin = window.location.origin;

    if (e.origin !== allowedOrigin) {
    console.warn('Blocked message from unauthorized origin:', e.origin);
    return;
    }

    if (e.data === 'close-chat') {
      closeChat();
    } else if (e.data === 'back-to-chats') {
      chatFrame.src = '/chat/landing/?frame=1';
    }
  });
});
