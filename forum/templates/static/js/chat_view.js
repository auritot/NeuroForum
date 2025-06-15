// static/js/chat_view.js

document.addEventListener("DOMContentLoaded", () => {
  const chatForm       = document.querySelector("#chat-form");
  const chatInput      = document.querySelector("#chat-input");
  const chatBox        = document.querySelector("#chat-box");
  const chatPlaceholder = document.getElementById("chat-placeholder");
  if (!chatForm || !chatInput || !chatBox) {
    console.error("Missing #chat-form, #chat-input, or #chat-box!");
    return;
  }

  const mainEl      = document.querySelector("main");
  const currentUser = (mainEl.dataset.currentUser || "").trim().toLowerCase();
  const otherUser   = (mainEl.dataset.otherUser   || "").trim().toLowerCase();

  // build WS URL
  const protocol   = window.location.protocol === "https:" ? "wss" : "ws";
  const wsUrl      = `${protocol}://${window.location.host}/ws/chat/${otherUser}/`;
  const chatSocket = new WebSocket(wsUrl);

  // on open, notify parent that this thread is active (mark it read)
  chatSocket.addEventListener("open", () => {
    window.parent.postMessage({ type: "chat-read", from: otherUser }, "*");
  });

  let sawPlaceholder = false;
  function appendBubble({ message, sender, timestamp }) {
    const isSelf    = sender.toLowerCase() === currentUser;
    const wrapper   = document.createElement("div");
    wrapper.classList.add("d-flex", isSelf ? "justify-content-end" : "justify-content-start", "mb-2");

    const bubble    = document.createElement("div");
    bubble.classList.add("p-2", isSelf ? "bg-light text-dark" : "bg-primary text-white", "rounded");
    bubble.textContent = message;

    const ts        = document.createElement("div");
    ts.classList.add("small", "text-muted", "mt-1");
    ts.textContent = timestamp;

    bubble.appendChild(ts);
    wrapper.appendChild(bubble);
    chatBox.appendChild(wrapper);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  chatSocket.addEventListener("message", e => {
    const data = JSON.parse(e.data);

    if (data.history) {
      // initial backlog
      data.history.forEach(msg => appendBubble(msg));
    }
    else if (data.message) {
      // a live message in THIS thread
      if (!sawPlaceholder && chatPlaceholder) {
        chatBox.removeChild(chatPlaceholder);
        sawPlaceholder = true;
      }
      appendBubble(data);
    }
    else if (data.type === "notify") {
      // an unread‐badge ping for other threads
      window.parent.postMessage({ type: "new-message", from: data.from }, "*");
    }
  });

  chatForm.addEventListener("submit", e => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text || chatSocket.readyState !== WebSocket.OPEN) {
      chatInput.focus();
      return;
    }
    chatSocket.send(JSON.stringify({ message: text }));
    chatInput.value = "";
    chatInput.focus();
  });
});
