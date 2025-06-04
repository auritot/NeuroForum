# forum/consumers.py

import json
import bleach
import time
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from django.utils import timezone

from .models import ChatRoom, ChatSession, ChatMessage

logger = logging.getLogger(__name__)


class PrivateChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 1. Authenticate as before
        user = self.scope["user"]
        if not user or not hasattr(user, "is_authenticated") or not user.is_authenticated:
            await self.close(code=4001)
            return

        # 2. Determine other_user and room name (lowercased)
        self.other_user = self.scope["url_route"]["kwargs"]["username"].lower()
        self.current_user = user.username.lower()
        a, b = sorted([self.current_user, self.other_user])
        room_name = f"private_{a}_{b}"
        self.room_name = room_name

        # 3. Fetch or create the ChatRoom
        self.chatroom = await database_sync_to_async(ChatRoom.get_or_create_private)(a, b)

        # 4. Find any open session (ChatSession with ended_at is NULL)
        self.session = await self.get_or_create_open_session(self.chatroom)

        # 5. (Optional) Check if user is permitted to chat with other_user.
        #    If you have special logic, put it here. Otherwise skip.
        if not await self.user_can_chat_with(user, self.other_user):
            await self.close(code=4003)
            return

        # 6. Track “how many participants are in this session” in Redis or in‐memory.
        #    For simplicity, we’ll keep an in‐memory counter here keyed by session.id.
        #    Note: In production, if you run multiple Daphne workers, you’d use Redis.
        self.rate_limit_interval = 0.2
        self.last_message_time = 0.0

        # 7. Join the group
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

        # 8. Increment the “connected participants” count for this session.
        count = await self.increment_participant_count(self.session.id)

        # 9. If count == 1, that means “this user is the first to join an open session”— 
        #    so we already created it in get_or_create_open_session(). If count > 1, 
        #    we’re just a second+ participant in that same session.

        # 10. Send existing “history” (all messages from any *ended* sessions) to the client:
        past = await self.fetch_messages_from_ended_sessions(self.chatroom)
        for msg in past:
            await self.send(text_data=json.dumps({
                "message": msg.content,
                "sender": msg.sender.username,
                "timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M"),
                "history": True,
                "session_range": f"{msg.session.started_at:%Y-%m-%d %H:%M} → {msg.session.ended_at:%Y-%m-%d %H:%M}"
            }))

        # 11. Send the “current session” backlog (in case this user joined late):
        current_backlog = await self.fetch_messages_from_session(self.session)
        for msg in current_backlog:
            await self.send(text_data=json.dumps({
                "message": msg.content,
                "sender": msg.sender.username,
                "timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M"),
                "history": False,
            }))

    async def disconnect(self, close_code):
        # 1. Leave the group
        if hasattr(self, "room_name"):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

        # 2. Decrement the participant count for this session:
        remaining = await self.decrement_participant_count(self.session.id)
        #    If remaining == 0, that means “no one is left in this session” → close it
        if remaining == 0:
            await self.close_session(self.session)

        logger.info(f"[DISCONNECT] user={self.current_user}, room={self.room_name}, remaining={remaining}")

    async def receive(self, text_data):
        # 1. Throttle
        now = time.time()
        if now - self.last_message_time < self.rate_limit_interval:
            return
        self.last_message_time = now

        # 2. Parse + validate JSON
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        raw_message = data.get("message", "")
        if not isinstance(raw_message, str) or len(raw_message) > 2048:
            return

        # 3. Sanitize
        safe_message = bleach.clean(raw_message)

        # 4. Broadcast to group
        await self.channel_layer.group_send(
            self.room_name,
            {
                "type": "chat_message",
                "message": safe_message,
                "sender": self.current_user,
                "history": False,   # indicates this message belongs to an open session
            }
        )

        # 5. Persist to DB, attached to the current ChatSession
        await self.save_message(self.session, self.scope["user"], safe_message)

    async def chat_message(self, event):
        """
        Called whenever group_send triggers. Simply relay to WebSocket.
        """
        await self.send(text_data=json.dumps({
            "message": event["message"],
            "sender": event["sender"],
            "history": event.get("history", False),
            # We could add local timestamp here, but historical messages already have server timestamp
        }))

    #
    # ─── Helper Methods (annotated with @database_sync_to_async) ─────────────────────────────────
    #

    @database_sync_to_async
    def get_or_create_open_session(self, chatroom):
        """
        Look for a ChatSession in this room where ended_at IS NULL.
        If none exists, create one (with ended_at = None → meaning “open”).
        Returns that ChatSession instance.
        """
        open_session = ChatSession.objects.filter(room=chatroom, ended_at__isnull=True).first()
        if open_session:
            return open_session
        # If no open session, create a new one
        session = ChatSession.objects.create(room=chatroom)
        return session

    @database_sync_to_async
    def close_session(self, session: ChatSession):
        """
        Mark this session as ended (set ended_at = now).
        """
        session.ended_at = timezone.now()
        session.save()

    @database_sync_to_async
    def save_message(self, session: ChatSession, user, content: str):
        """
        Create a ChatMessage row under this session.
        """
        ChatMessage.objects.create(session=session, sender=user, content=content)

    @database_sync_to_async
    def fetch_messages_from_ended_sessions(self, chatroom):
        """
        Fetch all ChatMessages whose session has ended (ended_at != NULL),
        sorted oldest → newest across *all* past sessions in this room.
        If you only want the last N, you can slice here.
        """
        # We do a join: ChatMessage → ChatSession → filter ended_at__isnull=False
        qs = ChatMessage.objects.filter(
            session__room=chatroom,
            session__ended_at__isnull=False
        ).select_related("session", "sender").order_by("session__started_at", "timestamp")
        return list(qs)

    @database_sync_to_async
    def fetch_messages_from_session(self, session: ChatSession):
        """
        Fetch all ChatMessages in the currently open session, in chronological order.
        """
        qs = ChatMessage.objects.filter(session=session).select_related("sender").order_by("timestamp")
        return list(qs)

    @database_sync_to_async
    def user_can_chat_with(self, user, other_username):
        """
        Implement your business logic. For example, only allow if a ChatRoom already exists
        or these two are “friends,” etc. If you don’t need extra checks, you can `return True`.
        """
        # Example: check that other_username corresponds to a real user, etc.
        from .models import ChatRoom
        try:
            # If your ChatRoom.get_or_create_private logic ensures only valid users can chat,
            # you can simply `return True`. Otherwise, do your checks here.
            return True
        except:
            return False

    #
    # ─── Participant Counting (in‐memory demo; use Redis in prod) ──────────────────────────────
    #

    _session_participants = {}  # { session_id: count_of_connected }

    @database_sync_to_async
    def increment_participant_count(self, session_id: int) -> int:
        """
        Increments the in-memory counter for session_id. Returns new count.
        In a multi-worker setup, you’d use Redis/DB instead of a class‐var dict.
        """
        cnt = PrivateChatConsumer._session_participants.get(session_id, 0) + 1
        PrivateChatConsumer._session_participants[session_id] = cnt
        return cnt

    @database_sync_to_async
    def decrement_participant_count(self, session_id: int) -> int:
        """
        Decrements the in-memory counter; returns new count.
        If count hits zero, we know “last user left.”
        """
        cnt = PrivateChatConsumer._session_participants.get(session_id, 0) - 1
        if cnt <= 0:
            PrivateChatConsumer._session_participants.pop(session_id, None)
            return 0
        PrivateChatConsumer._session_participants[session_id] = cnt
        return cnt
