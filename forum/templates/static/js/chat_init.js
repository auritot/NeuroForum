// static/js/chat_init.js

// —————————————
// helper to pull CSRF token from cookies
// —————————————
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

  // —————————————
  // listen for messages FROM the iframe
  // —————————————
  window.addEventListener("message", event => {
    const { type, from } = event.data || {};
    const who = (from || "").toLowerCase();
    const link = threadLinks.find(l => (l.dataset.user || "").toLowerCase() === who);
    if (!link) return;

    if (type === "chat-read") {
      // clear the badge on that link
      const badge = link.querySelector(".unread-count");
      if (badge) {
        badge.textContent = "0";
        badge.classList.add("d-none");
      }
      link.classList.remove("has-unread");

      // if none left, kill the glow
      if (!threadLinks.some(l => l.classList.contains("has-unread"))) {
        chatBtn.classList.remove("has-notification");
      }

      // tell server to zero out unread
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
      // bump the badge
      const badge = link.querySelector(".unread-count");
      const count = (parseInt(badge.textContent, 10) || 0) + 1;
      badge.textContent = count;
      badge.classList.remove("d-none");
      link.classList.add("has-unread");
      chatBtn.classList.add("has-notification");
    }
  });

  // —————————————
  // when you click on a thread in the sidebar
  // —————————————
  threadLinks.forEach(link => {
    link.addEventListener("click", () => {
      const who = link.dataset.user;              // <-- was dataset.threadUser

      // 1) clear UI badge
      const badge = link.querySelector(".unread-count");
      if (badge) {
        badge.textContent = "0";
        badge.classList.add("d-none");
      }
      link.classList.remove("has-unread");
      if (!threadLinks.some(l => l.classList.contains("has-unread"))) {
        chatBtn.classList.remove("has-notification");
      }

      // 2) clear server-side unread
      fetch(`/chat/${who}/mark-read/`, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
          "Content-Type": "application/json",
        },
      });

      // 3) highlight active link
      threadLinks.forEach(l => l.classList.remove("active-thread"));
      link.classList.add("active-thread");

      // 4) load the iframe — build URL yourself
      chatFrame.src = `/chat/${who}/?frame=1`;
      chatBox.classList.remove("d-none");
    });
  });

  // —————————————
  // open/close the floating panel
  // —————————————
  closeBtn.addEventListener("click", () => {
    chatBox.classList.add("d-none");
    chatFrame.src = "";
  });
  chatBtn.addEventListener("click", () => {
    chatBox.classList.toggle("d-none");
  });
});
