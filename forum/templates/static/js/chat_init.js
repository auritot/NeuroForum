// static/js/chat_init.js

document.addEventListener("DOMContentLoaded", () => {
  // ────────────────────────────────────────────────────────────────
  // 1) Populate the overlay 'Existing Chats' list via fetch
  // ────────────────────────────────────────────────────────────────
  const overlayContainer = document.getElementById("overlay-existing-chats");
  if (overlayContainer) {
    fetch("/api/chat/threads/", { credentials: "include" })
      .then(resp => {
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return resp.json();
      })
      .then(json => {
        // clear the placeholder (<li>No chats yet</li> or similar)
        overlayContainer.innerHTML = "";

        if (!Array.isArray(json.threads) || !json.threads.length) {
          // show empty state
          const li = document.createElement("li");
          li.classList.add("text-white-50");
          li.innerHTML = "<em>No chats yet</em>";
          overlayContainer.appendChild(li);
          return;
        }

        // inject one <li><a…> per partner
        json.threads.forEach(user => {
          const li = document.createElement("li");
          const a  = document.createElement("a");

          a.href = "#";
          a.textContent = user;
          a.classList.add("chat-thread-link");
          a.dataset.user = user.toLowerCase();
          a.addEventListener("click", e => {
            e.preventDefault();
            openChat(user);
          });

          li.appendChild(a);
          overlayContainer.appendChild(li);
        });
      })
      .catch(err => {
        console.error("Failed to load chat threads:", err);
      });
  }

  // ────────────────────────────────────────────────────────────────
  // 2) Wire up 'Start New Chat' in the overlay
  // ────────────────────────────────────────────────────────────────
  const sidebarForm = document.querySelector("form[action$='start_chat']");
  if (sidebarForm) {
    sidebarForm.addEventListener("submit", e => {
      e.preventDefault();
      const userInput = document.getElementById("sidebarUsernameIframe");
      if (userInput && userInput.value.trim()) {
        openChat(userInput.value.trim());
      }
    });
  }

  // ────────────────────────────────────────────────────────────────
  // 3) Wire up any thread-link clicks that already exist on the page
  // ────────────────────────────────────────────────────────────────
  const threadLinks = Array.from(document.querySelectorAll(".chat-thread-link"));
  threadLinks.forEach(el => {
    el.addEventListener("click", e => {
      e.preventDefault();
      openChat(el.dataset.user);
    });
  });
});
