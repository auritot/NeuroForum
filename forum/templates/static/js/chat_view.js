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

  // Build the WS URL (use wss:// on HTTPS pages)
  const wsProtocol = (window.location.protocol === "https:") ? "wss://" : "ws://";
  const wsUrl      = wsProtocol + window.location.host + "/ws/chat/" + otherUser + "/";
  const chatSocket = new WebSocket(wsUrl);

  // Flag to track whether we've removed the “Loading…” placeholder
  let sawAnyMessage = false;

  // Helper: append a chat bubble to #chat-box
  function appendBubble(parentEl, data, isSelf) {
    const alignClass = isSelf ? "justify-content-end" : "justify-content-start";
    const bubbleType = isSelf ? "self" : "other";

    // If the server provided a timestamp (formatted "HH:MM DD/MM/YYYY"), show it
    const timeHtml = data.timestamp
      ? `<br><small class="text-muted">${data.timestamp}</small>`
      : "";

    const msgHtml = `
      <div class="d-flex ${alignClass}">
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
    const data = JSON.parse(event.data);

    // On the very first message (history or live), remove the placeholder
    if (!sawAnyMessage) {
      const ph = document.querySelector("#chat-placeholder");
      if (ph) ph.remove();
      sawAnyMessage = true;
    }

    // Determine if this was “history” or “current”—but in both cases,
    // we just append to the same #chat-box.
    const sender = (data.sender || "").toLowerCase();
    const isSelf = (sender === currentUser);

    // Append the bubble
    appendBubble(chatBox, data, isSelf);
  });

  // On form submit: optimistically echo, send to server, and refocus
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

    // Build a “fake” payload so the user sees their own bubble immediately
    const now    = new Date();
    const hhmm   = now.toLocaleTimeString("en-GB", { hour12: false, hour: "2-digit", minute: "2-digit" });
    const ddmmyy = now.toLocaleDateString("en-GB");
    const fakePayload = {
      message: text,
      sender: currentUser,
      timestamp: `${hhmm} ${ddmmyy}`,
      history: false
    };

    // On first-ever live message, remove placeholder:
    if (!sawAnyMessage) {
      const ph = document.querySelector("#chat-placeholder");
      if (ph) ph.remove();
      sawAnyMessage = true;
    }

    // Append right away:
    appendBubble(chatBox, fakePayload, /* isSelf= */ true);

    // Then actually send to the server. When the server broadcasts it back,
    // our “message” listener will append it again (you can choose to filter duplicates
    // if you want, but double‐rendering is harmless).
    chatSocket.send(JSON.stringify({ message: text }));

    chatInput.value = "";
    chatInput.focus();
  });
});
