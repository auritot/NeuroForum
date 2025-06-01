document.addEventListener("DOMContentLoaded", function () {
    const chatForm = document.querySelector("#chat-form");
    const chatInput = document.querySelector("#chat-input");
    const chatLog = document.querySelector("#chat-box");

    if (!chatForm || !chatInput || !chatLog) return;

    const mainEl = document.querySelector("main");
    const currentUser = mainEl?.dataset.currentUser || "";
    const otherUser = mainEl?.dataset.otherUser || "";

    console.log("currentUser:", currentUser);
    console.log("otherUser:", otherUser);

    const chatSocket = new WebSocket(
        (window.location.protocol === "https:" ? "wss://" : "ws://") +
        window.location.host +
        "/ws/chat/" + otherUser + "/"
    );

    chatSocket.onopen = () => {
        console.log("✅ WebSocket connected");
    };

    chatSocket.onerror = (err) => {
        console.error("❌ WebSocket error:", err);
    };

    chatSocket.onmessage = function (e) {
        const data = JSON.parse(e.data);
        const isSelf = data.sender.toLowerCase() === currentUser;
        const msgHtml = `
        <div class="d-flex ${isSelf ? 'justify-content-end' : 'justify-content-start'} mb-2">
            <div class="p-2 rounded bg-${isSelf ? 'primary text-white' : 'light'}" style="max-width: 75%;">
                <small><strong>${data.sender}</strong></small><br>
                ${data.message}
            </div>
        </div>`;
        chatLog.innerHTML += msgHtml;
        chatLog.scrollTop = chatLog.scrollHeight;
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
