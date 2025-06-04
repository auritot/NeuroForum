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
    _session_participants = {}

    async def connect(self):
        user = self.scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            await self.close(code=4001)
            return

        self.other_user   = self.scope["url_route"]["kwargs"]["username"].lower()
        self.current_user = user.username.lower()
        a, b = sorted([self.current_user, self.other_user])
        self.room_name = f"private_{a}_{b}"

        self.chatroom = await database_sync_to_async(ChatRoom.get_or_create_private)(a, b)
        self.session  = await self.get_or_create_open_session(self.chatroom)

        if not await self.user_can_chat_with(user, self.other_user):
            await self.close(code=4003)
            return

        self.rate_limit_interval = 0.2
        self.last_message_time   = 0.0

        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

        count = await self.increment_participant_count(self.session.id)
        logger.info(f"[CONNECT] user={self.current_user}, room={self.room_name}, participants={count}")

        # 1) Send past (ended) sessions
        past = await self.fetch_messages_from_ended_sessions(self.chatroom)
        if not past:
            # If no history, send a dummy placeholder so JS can detect "no history"
            await self.send(text_data=json.dumps({ "history": True }))
        else:
            for msg in past:
                await self.send(text_data=json.dumps({
                    "message":       msg.content,
                    "sender":        msg.sender.username,
                    "timestamp":     msg.timestamp.strftime("%H:%M %d/%m/%Y"),
                    "history":       True,
                    "session_range": f"{msg.session.started_at.strftime('%H:%M %d/%m/%Y')} → {msg.session.ended_at.strftime('%H:%M %d/%m/%Y')}"
                }))

        # 2) Send any backlog from currently open session
        current_backlog = await self.fetch_messages_from_session(self.session)
        for msg in current_backlog:
            await self.send(text_data=json.dumps({
                "message":   msg.content,
                "sender":    msg.sender.username,
                "timestamp": msg.timestamp.strftime("%H:%M %d/%m/%Y"),
                "history":   False,
            }))

    async def receive(self, text_data):
        now = time.time()
        if now - self.last_message_time < self.rate_limit_interval:
            return
        self.last_message_time = now

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        raw_message = data.get("message", "")
        if not isinstance(raw_message, str) or len(raw_message) > 2048:
            return

        safe_message = bleach.clean(raw_message)
        timestamp_str = timezone.now().strftime("%H:%M %d/%m/%Y")

        # Broadcast to group, including the server timestamp
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

        # Persist in the database
        await self.save_message(self.session, self.scope["user"], safe_message)

    async def chat_message(self, event):
        """
        Handler that re-sends to each WebSocket in the group.
        Now *includes* 'timestamp' so everyone sees the same server-generated time.
        """
        await self.send(text_data=json.dumps({
            "message":   event["message"],
            "sender":    event["sender"],
            "history":   event.get("history", False),
            "timestamp": event.get("timestamp")
        }))

    async def disconnect(self, close_code):
        if hasattr(self, "room_name"):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

        remaining = await self.decrement_participant_count(self.session.id)
        if remaining == 0:
            await self.close_session(self.session)
        logger.info(f"[DISCONNECT] user={self.current_user}, room={self.room_name}, remaining={remaining}")

    @database_sync_to_async
    def get_or_create_open_session(self, chatroom):
        open_session = ChatSession.objects.filter(room=chatroom, ended_at__isnull=True).first()
        if open_session:
            return open_session
        return ChatSession.objects.create(room=chatroom)

    @database_sync_to_async
    def close_session(self, session: ChatSession):
        session.ended_at = timezone.now()
        session.save()

    @database_sync_to_async
    def save_message(self, session: ChatSession, user, content: str):
        ChatMessage.objects.create(session=session, sender=user, content=content)

    @database_sync_to_async
    def fetch_messages_from_ended_sessions(self, chatroom):
        qs = ChatMessage.objects.filter(
            session__room=chatroom,
            session__ended_at__isnull=False
        ).select_related("session", "sender").order_by("session__started_at", "timestamp")
        return list(qs)

    @database_sync_to_async
    def fetch_messages_from_session(self, session: ChatSession):
        qs = ChatMessage.objects.filter(session=session).select_related("sender").order_by("timestamp")
        return list(qs)

    @database_sync_to_async
    def user_can_chat_with(self, user, other_username):
        return True

    @database_sync_to_async
    def increment_participant_count(self, session_id: int) -> int:
        cnt = PrivateChatConsumer._session_participants.get(session_id, 0) + 1
        PrivateChatConsumer._session_participants[session_id] = cnt
        return cnt

    @database_sync_to_async
    def decrement_participant_count(self, session_id: int) -> int:
        cnt = PrivateChatConsumer._session_participants.get(session_id, 0) - 1
        if cnt <= 0:
            PrivateChatConsumer._session_participants.pop(session_id, None)
            return 0
        PrivateChatConsumer._session_participants[session_id] = cnt
        return cnt
