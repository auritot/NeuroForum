// static/js/chat_view.js

document.addEventListener("DOMContentLoaded", () => {
  const chatForm = document.querySelector("#chat-form");
  const chatInput = document.querySelector("#chat-input");
  const chatBox = document.querySelector("#chat-box");

  // Pull <main data-...> attributes
  const mainEl = document.querySelector("main");
  const currentUser = (mainEl.dataset.currentUser || "").trim().toLowerCase();
  const otherUser = (mainEl.dataset.otherUser || "").trim().toLowerCase();

  // Build the proper WSS/WS URL.  If the page is HTTPS, use wss://, otherwise ws://
  const wsProtocol = (window.location.protocol === "https:") ? "wss://" : "ws://";
  const wsUrl = wsProtocol + window.location.host + "/ws/chat/" + otherUser + "/";

  const chatSocket = new WebSocket(wsUrl);

  // This flag tells us whether we've already removed the “Loading previous chats…” placeholder
  let sawPlaceholder = false;

  // Helper to append a message bubble into #chat-box
  function appendBubble(parentEl, data, isSelf) {
    const alignClass = isSelf ? "justify-content-end" : "justify-content-start";
    const bubbleType = isSelf ? "self" : "other";

    // Create wrapper div
    const wrapperDiv = document.createElement("div");
    wrapperDiv.classList.add("d-flex", alignClass, "mb-2");

    // Create chat bubble div
    const bubbleDiv = document.createElement("div");
    bubbleDiv.classList.add("chat-bubble", bubbleType);

    // Sender
    const senderEl = document.createElement("small");
    const senderStrong = document.createElement("strong");
    senderStrong.textContent = data.sender;
    senderEl.appendChild(senderStrong);
    bubbleDiv.appendChild(senderEl);
    bubbleDiv.appendChild(document.createElement("br"));

    // Message
    const messageText = document.createTextNode(data.message);
    bubbleDiv.appendChild(messageText);

    // Timestamp (optional)
    if (data.timestamp) {
      bubbleDiv.appendChild(document.createElement("br"));
      const timeSmall = document.createElement("small");
      timeSmall.classList.add("timestamp");
      timeSmall.textContent = data.timestamp;
      bubbleDiv.appendChild(timeSmall);
    }

    // Combine and insert
    wrapperDiv.appendChild(bubbleDiv);
    parentEl.appendChild(wrapperDiv);
    parentEl.scrollTop = parentEl.scrollHeight;
  }


  chatSocket.addEventListener("message", (event) => {
    let data;
    try {
      data = JSON.parse(event.data);
    } catch {
      return;
    }

    if (data.type === "thread_list") {
      const container = document.getElementById("chat-threads");
      container.innerHTML = "";  // clear “No chats yet”

      data.threads.forEach(t => {
        const a = document.createElement("a");
        a.href = "#";
        a.classList.add("chat-thread-link");
        a.dataset.user = t.other_user.toLowerCase();
        a.textContent = t.other_user;
        a.addEventListener("click", () => openChat(t.other_user));
        container.appendChild(a);
      });
      return;
    }

    // On the very first incoming frame, remove the “Loading…” placeholder
    if (!sawPlaceholder) {
      const ph = document.querySelector("#chat-placeholder");
      if (ph) ph.remove();
      sawPlaceholder = true;
    }

    // If the server deliberately sent { history: true } with NO message/sender,
    // that is just our “no history” placeholder.  We silently ignore it.
    if (!data.message || !data.sender) {
      return;
    }

    // Otherwise, we have a real bubble.  Lowercase the sender to check if it was from us
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
      // console.error("WebSocket is not open; cannot send.");
      return;
    }

    // Build our JSON payload
    const payload = { message: text };
    // console.log("⟶ WS send:", JSON.stringify(payload));
    chatSocket.send(JSON.stringify(payload));

    // Clear & refocus
    chatInput.value = "";
    chatInput.focus();
  });
});
