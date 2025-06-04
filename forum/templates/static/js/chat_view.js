// static/js/chat_view.js

document.addEventListener("DOMContentLoaded", () => {
  const chatForm  = document.querySelector("#chat-form");
  const chatInput = document.querySelector("#chat-input");
  const chatBox   = document.querySelector("#chat-box");

  if (!chatForm || !chatInput || !chatBox) {
    console.error("Missing #chat-form, #chat-input, or #chat-box!");
    return;
  }

  // Pull usernames from <main data-...>
  const mainEl      = document.querySelector("main");
  const currentUser = (mainEl.dataset.currentUser || "").trim().toLowerCase();
  const otherUser   = (mainEl.dataset.otherUser   || "").trim().toLowerCase();

  // Build the WebSocket URL
  const wsProtocol = (window.location.protocol === "https:") ? "wss://" : "ws://";
  const wsUrl      = wsProtocol + window.location.host + "/ws/chat/" + otherUser + "/";
  const chatSocket = new WebSocket(wsUrl);

  // Tracks whether we’ve removed the “Loading previous chats…” placeholder
  let sawPlaceholder = false;

  // Helper to append a chat bubble
  function appendBubble(parentEl, data, isSelf) {
    const alignClass = isSelf ? "justify-content-end" : "justify-content-start";
    const bubbleType = isSelf ? "self" : "other";

    // Use the server-provided timestamp (format "HH:MM dd/mm/YYYY")
    const timeHtml = data.timestamp
      ? `<br><small class="text-muted">${data.timestamp}</small>`
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
    console.log("⟵ WS frame received:", event.data);
    let data;
    try {
      data = JSON.parse(event.data);
    } catch (_e) {
      console.error("Failed to parse frame as JSON:", event.data);
      return;
    }

    // On the very first frame (whether placeholder or real), remove placeholder
    if (!sawPlaceholder) {
      const ph = document.querySelector("#chat-placeholder");
      if (ph) ph.remove();
      sawPlaceholder = true;
    }

    // If there is no data.message or no data.sender, it’s our “no history” placeholder.
    // Just return silently.
    if (!data.message || !data.sender) {
      return;
    }

    // Otherwise, append a real bubble. Use data.sender & data.timestamp from the server.
    const sender = data.sender.toLowerCase();
    const isSelf = (sender === currentUser);
    appendBubble(chatBox, data, isSelf);
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

    // Before sending, log it so we can confirm in devtools what went out
    const payload = { message: text };
    console.log("⟶ WS send:", JSON.stringify(payload));
    chatSocket.send(JSON.stringify(payload));

    // Clear and refocus the input. We’ll let the server echo back a single bubble
    chatInput.value = "";
    chatInput.focus();
  });
});
