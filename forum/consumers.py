import json
import time
import bleach
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

from .models import ChatRoom, ChatSession, ChatMessage

logger = logging.getLogger(__name__)

class PrivateChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that supports:
      - Sending the full chat history (past/ended sessions) on connect
      - Carrying on the current open session (history=False)
      - Broadcasting new messages to everyone in the same private room
      - Persisting messages under a ChatSession
      - Closing a session when all participants disconnect
      - Rate-limiting so users can send at most ~5 messages per second
    """

    # In-memory counter of participants per ChatSession ID (for single-worker setups)
    _session_participants = {}

    async def connect(self):
        # 1. Authenticate the user
        user = self.scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            # Reject connection if not authenticated
            await self.close(code=4001)
            return

        # 2. Determine "other_user" from the URL, lowercase both names, and build unique room_name
        self.other_user = self.scope["url_route"]["kwargs"]["username"].lower()
        self.current_user = user.username.lower()
        user_pair = sorted([self.current_user, self.other_user])
        self.room_name = f"private_{user_pair[0]}_{user_pair[1]}"

        # 3. Fetch or create the ChatRoom object for these two users
        self.chatroom = await database_sync_to_async(ChatRoom.get_or_create_private)(
            user_pair[0], user_pair[1]
        )

        # 4. Fetch or create the open ChatSession for this room (ended_at is NULL)
        self.session = await self.get_or_create_open_session(self.chatroom)

        # 5. (Optional) Verify that these two users are permitted to chat
        if not await self.user_can_chat_with(user, self.other_user):
            await self.close(code=4003)
            return

        # 6. Rate-limit: allow one message every 0.2 seconds (5 messages per second)
        self.rate_limit_interval = 0.2
        self.last_message_time = 0.0

        # 7. Add this connection to the group and accept the WebSocket
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

        # 8. Increment the in-memory participant count for this session
        count = await self.increment_participant_count(self.session.id)
        logger.info(f"[CONNECT] user={self.current_user}, room={self.room_name}, participants={count}")

        # 9. Send all messages from ended sessions (history=True)
        past_messages = await self.fetch_messages_from_ended_sessions(self.chatroom)
        if not past_messages:
            # If no past messages at all, send one placeholder so front-end can detect "no history"
            await self.send(text_data=json.dumps({ "history": True }))
        else:
            # Send each past message in chronological order
            for msg in past_messages:
                await self.send(text_data=json.dumps({
                    "message":       msg.content,
                    "sender":        msg.sender.username,
                    "timestamp":     msg.timestamp.strftime("%H:%M %d/%m/%Y"),
                    "history":       True,
                    "session_range": f"{msg.session.started_at.strftime('%H:%M %d/%m/%Y')} → {msg.session.ended_at.strftime('%H:%M %d/%m/%Y')}"
                }))

        # 10. Send any backlog from the currently open session (history=False)
        current_backlog = await self.fetch_messages_from_session(self.session)
        for msg in current_backlog:
            await self.send(text_data=json.dumps({
                "message":   msg.content,
                "sender":    msg.sender.username,
                "timestamp": msg.timestamp.strftime("%H:%M %d/%m/%Y"),
                "history":   False
            }))

    async def receive(self, text_data):
        # 1. Rate-limit: drop if messages come too fast
        now = time.time()
        if now - self.last_message_time < self.rate_limit_interval:
            return
        self.last_message_time = now

        # 2. Parse incoming JSON
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        raw_message = data.get("message", "")
        if not isinstance(raw_message, str) or len(raw_message) > 2048:
            return

        # 3. Sanitize via bleach
        safe_message = bleach.clean(raw_message)

        # 4. Broadcast to the group, marking history=False
        timestamp_str = timezone.now().strftime("%H:%M %d/%m/%Y")
        await self.channel_layer.group_send(
            self.room_name,
            {
                "type":      "chat_message",
                "message":   safe_message,
                "sender":    self.current_user,
                "history":   False,
                "timestamp": timestamp_str
            }
        )

        # 5. Persist to the database under the open ChatSession
        await self.save_message(self.session, self.scope["user"], safe_message)

    async def chat_message(self, event):
        """
        Handler for "chat_message" group events. Re-send to WebSocket.
        """
        await self.send(text_data=json.dumps({
            "message":   event["message"],
            "sender":    event["sender"],
            "history":   event.get("history", False),
            "timestamp": event.get("timestamp")
        }))

    async def disconnect(self, close_code):
        # 1. Remove from group
        if hasattr(self, "room_name"):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

        # 2. Decrement participant count; if last one left, close the session
        remaining = await self.decrement_participant_count(self.session.id)
        if remaining == 0:
            await self.close_session(self.session)

        logger.info(f"[DISCONNECT] user={self.current_user}, room={self.room_name}, remaining={remaining}")

    # ─── Helper Methods ─────────────────────────────────────────────────────────────────

    @database_sync_to_async
    def get_or_create_open_session(self, chatroom):
        """
        Return a ChatSession for this room where ended_at is NULL (open).
        If none exists, create a new one.
        """
        open_session = ChatSession.objects.filter(room=chatroom, ended_at__isnull=True).first()
        if open_session:
            return open_session
        return ChatSession.objects.create(room=chatroom)

    @database_sync_to_async
    def close_session(self, session: ChatSession):
        """
        Mark the given session as ended by setting ended_at to now.
        """
        session.ended_at = timezone.now()
        session.save()

    @database_sync_to_async
    def save_message(self, session: ChatSession, user, content: str):
        """
        Persist a new ChatMessage under the given ChatSession.
        """
        ChatMessage.objects.create(session=session, sender=user, content=content)

    @database_sync_to_async
    def fetch_messages_from_ended_sessions(self, chatroom):
        """
        Fetch all ChatMessages whose session has ended (ended_at != NULL),
        sorted by session.started_at then timestamp ascending.
        """
        qs = ChatMessage.objects.filter(
            session__room=chatroom,
            session__ended_at__isnull=False
        ).select_related("session", "sender").order_by(
            "session__started_at", "timestamp"
        )
        return list(qs)

    @database_sync_to_async
    def fetch_messages_from_session(self, session: ChatSession):
        """
        Fetch all ChatMessages for the open session (ordered by timestamp).
        """
        qs = ChatMessage.objects.filter(session=session).select_related("sender").order_by("timestamp")
        return list(qs)

    @database_sync_to_async
    def user_can_chat_with(self, user, other_username):
        """
        Return True if `user` is allowed to chat with `other_username`.
        Customize this to enforce friend lists or blocking as needed.
        """
        return True

    @database_sync_to_async
    def increment_participant_count(self, session_id: int) -> int:
        """
        Increment in-memory participant count for the session.
        Returns the new count.
        """
        cnt = PrivateChatConsumer._session_participants.get(session_id, 0) + 1
        PrivateChatConsumer._session_participants[session_id] = cnt
        return cnt

    @database_sync_to_async
    def decrement_participant_count(self, session_id: int) -> int:
        """
        Decrement in-memory participant count. If it reaches zero or below,
        remove the key and return 0. Otherwise return the updated count.
        """
        cnt = PrivateChatConsumer._session_participants.get(session_id, 0) - 1
        if cnt <= 0:
            PrivateChatConsumer._session_participants.pop(session_id, None)
            return 0
        PrivateChatConsumer._session_participants[session_id] = cnt
        return cnt
