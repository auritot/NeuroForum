// static/js/chat_view.js

document.addEventListener("DOMContentLoaded", () => {
  const chatForm  = document.querySelector("#chat-form");
  const chatInput = document.querySelector("#chat-input");
  const chatBox   = document.querySelector("#chat-box");

  if (!chatForm || !chatInput || !chatBox) {
    console.error("Missing #chat-form, #chat-input, or #chat-box!");
    return;
  }

  // Grab the current user and the peer from the <main> data attributes
  const mainEl     = document.querySelector("main");
  const currentUser = (mainEl.dataset.currentUser || "").trim().toLowerCase();
  const otherUser   = (mainEl.dataset.otherUser   || "").trim().toLowerCase();

  // Tell parent we opened this chat (so it can clear unread badges)
  window.parent.postMessage({
    type: "chat-read",
    from: otherUser
  }, "*");

  // Build WebSocket URL
  const wsProtocol = (window.location.protocol === "https:") ? "wss://" : "ws://";
  const wsUrl      = wsProtocol + window.location.host + "/ws/chat/" + otherUser + "/";
  const chatSocket = new WebSocket(wsUrl);

  let sawPlaceholder = false;

  function appendBubble(parentEl, data, isSelf) {
    const alignClass = isSelf ? "justify-content-end" : "justify-content-start";
    const bubbleType = isSelf ? "self" : "other";
    const timeHtml = data.timestamp
      ? `<br><small class="timestamp">${data.timestamp}</small>`
      : "";
    const msgHtml = `
      <div class="d-flex ${alignClass} mb-2">
        <div class="chat-bubble ${bubbleType}">
          <small><strong>${data.sender}</strong></small><br>
          ${data.message}
          ${timeHtml}
        </div>
      </div>`;
    parentEl.insertAdjacentHTML("beforeend", msgHtml);
    parentEl.scrollTop = parentEl.scrollHeight;
  }

  chatSocket.addEventListener("open", () => {
    console.log("✅ WebSocket connected to " + wsUrl);
  });

  chatSocket.addEventListener("error", (err) => {
    console.error("❌ WebSocket error:", err);
  });

  chatSocket.addEventListener("close", (e) => {
    console.warn("⚠️ WebSocket closed:", e);
  });

  chatSocket.addEventListener("message", (event) => {
    let data;
    try {
      data = JSON.parse(event.data);
    } catch (_e) {
      console.error("Failed to parse frame as JSON:", event.data);
      return;
    }

    // 1) Handle our custom "notify" event (fired by the consumer on unread)
    if (data.type === "notify" && data.from) {
      // forward to parent just like a new-message
      window.parent.postMessage({
        type: "new-message",
        from: data.from
      }, "*");
      return;  // don't treat it as a real chat bubble
    }

    // 2) The old "history" placeholder removal
    if (!sawPlaceholder) {
      const ph = document.querySelector("#chat-placeholder");
      if (ph) ph.remove();
      sawPlaceholder = true;
    }

    // 3) Ignore pure-history frames
    if (!data.message || !data.sender) {
      return;
    }

    // 4) Render real bubble
    const sender = data.sender.toLowerCase();
    const isSelf = (sender === currentUser);
    appendBubble(chatBox, data, isSelf);

    // 5) Notify parent it’s a real incoming chat
    if (!isSelf) {
      window.parent.postMessage({
        type: "new-message",
        from: sender
      }, "*");
    }
  });

  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) {
      chatInput.focus();
      return;
    }
    if (chatSocket.readyState !== WebSocket.OPEN) {
      console.error("WebSocket is not open; cannot send.");
      return;
    }
    chatSocket.send(JSON.stringify({ message: text }));
    chatInput.value = "";
    chatInput.focus();
  });
});
