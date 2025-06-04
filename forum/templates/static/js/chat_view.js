document.addEventListener("DOMContentLoaded", () => {
  const chatForm   = document.querySelector("#chat-form");
  const chatInput  = document.querySelector("#chat-input");
  const chatBox    = document.querySelector("#chat-box");
  const historyBox = document.querySelector("#history-box");

  if (!chatForm || !chatInput || !chatBox || !historyBox) {
    console.error("Missing one of #chat-form, #chat-input, #chat-box, or #history-box!");
    return;
  }

  // Grab usernames from the <main> data- attributes
  const mainEl     = document.querySelector("main");
  const currentUser = mainEl.dataset.currentUser.trim().toLowerCase();
  const otherUser   = mainEl.dataset.otherUser.trim().toLowerCase();

  // Build the correct WSS URL (use wss:// if page is https://)
  const wsProtocol = (window.location.protocol === "https:") ? "wss://" : "ws://";
  const wsUrl      = wsProtocol + window.location.host + "/ws/chat/" + otherUser + "/";

  const chatSocket = new WebSocket(wsUrl);

  // Track whether we've removed placeholders yet
  let historyPlaceholderGone = false;
  let currentPlaceholderGone = false;

  // Helper: append one message DOM‐bubble into a given parent (<div id="chat-box"> or <div id="history-box">)
  function appendBubble(parentEl, data, isSelf) {
    const alignClass = isSelf ? "justify-content-end" : "justify-content-start";
    const bubbleType = isSelf ? "self" : "other";

    // If data.timestamp exists, we'll render it as "HH:MM DD/MM/YYYY" under the message
    const timeHtml = data.timestamp
      ? `<br><small class="text-muted">${data.timestamp}</small>`
      : "";

    const msgHtml = `
      <div class="d-flex ${alignClass} mb-2">
        <div class="chat-bubble ${bubbleType} w-75">
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
    const isHistory = data.history === true;
    const sender   = data.sender.toLowerCase();
    const isSelf   = (sender === currentUser);

    // Remove the “Loading…” / “Waiting…” placeholder once we have at least one message of that type
    if (isHistory && !historyPlaceholderGone) {
      const ph = document.querySelector("#history-placeholder");
      if (ph) ph.remove();
      historyPlaceholderGone = true;
    }
    if (!isHistory && !currentPlaceholderGone) {
      const ph = document.querySelector("#current-placeholder");
      if (ph) ph.remove();
      currentPlaceholderGone = true;
    }

    // Append the bubble into either historyBox or chatBox
    if (isHistory) {
      appendBubble(historyBox, data, isSelf);
    } else {
      appendBubble(chatBox, data, isSelf);
    }
  });

  // On form submit, send to the server and also instantly echo a “local” bubble
  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;

    // If socket is not open, bail
    if (chatSocket.readyState !== WebSocket.OPEN) {
      console.error("WebSocket is not open; cannot send:", chatSocket.readyState);
      return;
    }

    // Build a “fake” data object to optimistically show immediately
    const fakePayload = {
      message: text,
      sender: currentUser,
      timestamp: new Date().toLocaleTimeString("en-GB").replace(/:\d{2}$/, "") + " " +
                 new Date().toLocaleDateString("en-GB"),  
      // “HH:MM DD/MM/YYYY” using locale “en-GB” (no seconds)
      history: false
    };
    // Remove the “Waiting for current chat…” placeholder (if it’s still there)
    if (!currentPlaceholderGone) {
      const ph = document.querySelector("#current-placeholder");
      if (ph) ph.remove();
      currentPlaceholderGone = true;
    }
    appendBubble(chatBox, fakePayload, /* isSelf= */ true);

    // Actually send to the server; the server’s echo will re‐draw in case anything changed
    chatSocket.send(JSON.stringify({ message: text }));
    chatInput.value = "";
  });
});
