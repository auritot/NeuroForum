// static/js/chat_init.js

// Helper to pull CSRF token from cookies (if you don’t already have one)
function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  return match ? decodeURIComponent(match[2]) : null;
}

document.addEventListener("DOMContentLoaded", () => {
  const chatBtn     = document.getElementById("chat-btn");
  const chatBox     = document.getElementById("chat-box-floating");
  const closeBtn    = document.getElementById("close-chat");
  const chatFrame   = document.getElementById("chat-frame");
  const threadLinks = Array.from(document.querySelectorAll(".chat-thread-link"));

  // 1) Listen for postMessage events from the inner chat iframe
  window.addEventListener("message", event => {
    const { type, from } = event.data || {};
    if (type === "chat-read") {
      const who = (from || "").toLowerCase();
      const link = threadLinks.find(l => (l.dataset.threadUser||"").toLowerCase() === who);
      if (!link) return;

      // hide badge & clear count
      const badge = link.querySelector(".unread-count");
      if (badge) {
        badge.textContent = "0";
        badge.classList.add("d-none");
      }
      link.classList.remove("has-unread");

      // if no threads left unread, kill the glow
      if (!threadLinks.some(l => l.classList.contains("has-unread"))) {
        chatBtn.classList.remove("has-notification");
      }

      // fire a quick AJAX to clear on the server
      fetch(`/chat/${who}/mark-read/`, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
          "Content-Type": "application/json",
        },
      });
    }
    else if (type === "new-message") {
      const who = (from || "").toLowerCase();
      const link = threadLinks.find(l => (l.dataset.threadUser||"").toLowerCase() === who);
      if (!link) return;

      const badge = link.querySelector(".unread-count");
      const count = parseInt(badge.textContent || "0", 10) + 1;
      badge.textContent = count;
      badge.classList.remove("d-none");
      link.classList.add("has-unread");
      chatBtn.classList.add("has-notification");
    }
  });

  // 2) When you click a thread: open it AND clear its unread immediately
  threadLinks.forEach(link => {
    link.addEventListener("click", () => {
      const who = link.dataset.threadUser;

      // clear UI
      const badge = link.querySelector(".unread-count");
      if (badge) {
        badge.textContent = "0";
        badge.classList.add("d-none");
      }
      link.classList.remove("has-unread");
      if (!threadLinks.some(l => l.classList.contains("has-unread"))) {
        chatBtn.classList.remove("has-notification");
      }

      // mark server‐side read
      fetch(`/chat/${who.toLowerCase()}/mark-read/`, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
          "Content-Type": "application/json",
        },
      });

      // activate thread visually
      threadLinks.forEach(l => l.classList.remove("active-thread"));
      link.classList.add("active-thread");

      // load the iframe
      chatFrame.src = link.dataset.url;
      chatBox.classList.remove("d-none");
    });
  });

  closeBtn.addEventListener("click", () => {
    chatBox.classList.add("d-none");
    chatFrame.src = "";
  });
  chatBtn.addEventListener("click", () => {
    chatBox.classList.toggle("d-none");
  });
});
