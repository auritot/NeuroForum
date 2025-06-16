document.addEventListener("DOMContentLoaded", () => {
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
    // chatFrame.src = "";
    // threadLinks.forEach(el => el.classList.remove("active-thread"));
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
      threadLinks.forEach(l => l.classList.remove("active-thread"));
      el.classList.add("active-thread");
      chatFrame.src = `/chat/${user}/?frame=1`;
      openChat();
    });
  });

  // helper to get CSRF cookie
// function getCookie(name) {
//   let v = document.cookie.match('(^|;)\\s*'+ name +'\\s*=\\s*([^;]+)');
//   return v ? v.pop() : '';
// }

// document.querySelectorAll(".delete-chat").forEach(btn => {
//   btn.addEventListener("click", e => {
//     e.preventDefault();
//     const user = btn.dataset.user;
//     if (!confirm(`Delete chat with ${user}? This cannot be undone.`)) return;

//     fetch(`/delete_chat/${user}/`, {
//       method: "POST",
//       headers: {
//         "X-CSRFToken": getCookie("csrftoken"),
//         "X-Requested-With": "XMLHttpRequest",
//         "Content-Type": "application/json"
//       },
//     })
//     .then(res => res.json())
//     .then(json => {
//       if (json.success) {
//         // remove that <li> from the sidebar
//         btn.closest("li").remove();
//         // if they were the active thread, also clear the iframe
//         if (btn.closest("li").querySelector(".active-thread")) {
//           document.getElementById("chat-frame").src = "";
//         }
//       } else {
//         alert(json.error || "Could not delete chat");
//       }
//     })
//     .catch(() => alert("Network error deleting chat"));
//   });
// });

  // hijack “Start New Chat” form
  const sidebarForm = document.querySelector("#chat-sidebar form");
  if (sidebarForm) {
    sidebarForm.addEventListener("submit", e => {
      e.preventDefault();
      const input = document.getElementById("sidebarUsernameIframe");
      const user  = input.value.trim().toLowerCase();
      if (!user) return;
      threadLinks.forEach(l => l.classList.remove("active-thread"));
      const match = threadLinks.find(l => l.dataset.user === user);
      if (match) match.classList.add("active-thread");
      chatFrame.src = `/chat/${user}/?frame=1`;

      // clear your “find user” box
      if (searchInput) searchInput.value = "";

      openChat();
    });
  }

  // keep the little “active” highlight in sync when the iframe reloads
  chatFrame.addEventListener("load", () => {
    chatFrame.classList.remove("loading");

    const m = chatFrame.src.match(/\/chat\/([^/]+)\//);
    if (m) {
      const active = m[1];
      threadLinks.forEach(el =>
        el.classList.toggle("active-thread", el.dataset.user === active)
      );
      if (searchInput) searchInput.value = "";
    }
  });
});
