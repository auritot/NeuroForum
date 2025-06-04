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

  // Have we removed the "Loading previous chats" placeholder yet?
  let sawPlaceholder = false;

  // Helper to append a single chat bubble to #chat-box
  function appendBubble(parentEl, data, isSelf) {
    const alignClass = isSelf ? "justify-content-end" : "justify-content-start";
    const bubbleType = isSelf ? "self" : "other";

    // If the server provided a timestamp ("HH:MM dd/mm/yyyy"), show it
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
    let data;
    try {
      data = JSON.parse(event.data);
    } catch (_e) {
      console.error("Failed to parse WebSocket JSON:", event.data);
      return;
    }

    // Remove the "Loading previous chats…" placeholder on the very first incoming frame
    if (!sawPlaceholder) {
      const ph = document.querySelector("#chat-placeholder");
      if (ph) ph.remove();
      sawPlaceholder = true;
    }

    // If there's no actual message text, do nothing further.
    // (This covers the "{ history: true }" placeholder your consumer sent when no history existed.)
    if (!data.message || !data.sender) {
      return;
    }

    const sender = data.sender.toLowerCase();
    const isSelf = (sender === currentUser);
    appendBubble(chatBox, data, isSelf);
  });

  // On form submit: send to server, echo locally, and keep focus
  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) {
      chatInput.focus();
      return;
    }

    if (chatSocket.readyState !== WebSocket.OPEN) {
      console.error("WebSocket is not open; cannot send message right now.");
      return;
    }

    // Build a quick "optimistic" payload with client-side timestamp
    const now    = new Date();
    const hhmm   = now.toLocaleTimeString("en-GB", {
      hour12: false,
      hour:   "2-digit",
      minute: "2-digit"
    });
    const ddmmyy = now.toLocaleDateString("en-GB"); // e.g. "dd/mm/yyyy"

    const fakePayload = {
      message:   text,
      sender:    currentUser,
      timestamp: `${hhmm} ${ddmmyy}`,
      history:   false
    };

    // If we haven't removed the placeholder yet (no frames), remove it now:
    if (!sawPlaceholder) {
      const ph = document.querySelector("#chat-placeholder");
      if (ph) ph.remove();
      sawPlaceholder = true;
    }

    // Immediately append Bob's bubble so he sees it right away
    appendBubble(chatBox, fakePayload, /* isSelf= */ true);

    // Actually send to the server. When the server broadcasts it back,
    // the callback above will append a second identical bubble.
    chatSocket.send(JSON.stringify({ message: text }));

    chatInput.value = "";
    chatInput.focus();
  });
});
