document.addEventListener("DOMContentLoaded", function () {
    const chatForm = document.querySelector("#chat-form");
    const chatInput = document.querySelector("#chat-input");
    const chatBox = document.querySelector("#chat-box");
    const historyBox = document.querySelector("#history-box");

    if (!chatForm || !chatInput || !chatBox || !historyBox) return;

    const mainEl = document.querySelector("main");
    const currentUser = mainEl.dataset.currentUser || "";
    const otherUser = mainEl.dataset.otherUser || "";

    console.log("currentUser:", currentUser);
    console.log("otherUser:", otherUser);

    const wsProtocol = (window.location.protocol === "https:") ? "wss://" : "ws://";
    const wsUrl = wsProtocol + window.location.host + "/ws/chat/" + otherUser + "/";
    const chatSocket = new WebSocket(wsUrl);

    chatSocket.onopen = () => {
        console.log("✅ WebSocket connected");
    };

    chatSocket.onerror = (err) => {
        console.error("❌ WebSocket error:", err);
    };

    chatSocket.onmessage = function (e) {
        const data = JSON.parse(e.data);
        const isHistory = data.history === true;
        const isSelf = data.sender.toLowerCase() === currentUser;
        const bubbleType = isSelf ? "self" : "other";
        const alignClass = isSelf ? "justify-content-end" : "justify-content-start";

        // If a timestamp was provided, show it (formatted as "HH:MM DD/MM/YYYY")
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

        if (isHistory) {
            // First history message? Remove placeholder
            const histPlaceholder = document.querySelector("#history-placeholder");
            if (histPlaceholder) histPlaceholder.remove();
            historyBox.innerHTML += msgHtml;
            historyBox.scrollTop = historyBox.scrollHeight;
        } else {
            // First current message? Remove placeholder
            const currPlaceholder = document.querySelector("#current-placeholder");
            if (currPlaceholder) currPlaceholder.remove();
            chatBox.innerHTML += msgHtml;
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    };

    chatForm.onsubmit = function (e) {
        e.preventDefault();
        const message = chatInput.value.trim();
        console.log("📨 Sending:", message, "readyState:", chatSocket.readyState);
        if (message && chatSocket.readyState === WebSocket.OPEN) {
            chatSocket.send(JSON.stringify({ message }));
            chatInput.value = "";
        }
    };
});
