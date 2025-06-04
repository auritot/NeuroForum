# forum/consumers.py
import json
import time
import bleach
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

from django.contrib.auth import get_user_model
from .models import ChatRoom, ChatSession, ChatMessage

logger = logging.getLogger(__name__)
User = get_user_model()


class PrivateChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for a two‐way private chat.
    The URL is /ws/chat/<other_username>/, and Django's AuthMiddlewareStack
    means `self.scope["user"]` is the currently logged‐in User.
    """

    # Keep track of how many open sockets each ChatSession has.
    # When the last socket disconnects, we mark the session as ‘ended’.
    _session_participants = {}

    async def connect(self):
        user = self.scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            # If not logged in, refuse connection
            await self.close(code=4001)
            return

        # The “other party” is the <username> captured in the URL (lowercased)
        self.other_user = self.scope["url_route"]["kwargs"]["username"].lower()
        self.current_user = user.username.lower()

        # Build a canonical room_name (sorted so that “alice‐bob” and “bob‐alice” map
        # to the SAME room).  Prefix with “private_” to avoid collisions.
        a, b = sorted([self.current_user, self.other_user])
        self.room_name = f"private_{a}_{b}"

        # Create or fetch the ChatRoom and the “currently open” ChatSession
        self.chatroom = await database_sync_to_async(ChatRoom.get_or_create_private)(a, b)
        self.session = await self._get_or_create_open_session(self.chatroom)

        # Optionally: check if user is allowed to chat with <other_user>.
        # In this example, we simply allow everyone:
        if not await self._user_can_chat_with(self.scope["user"], self.other_user):
            await self.close(code=4003)
            return

        # VERY IMPORTANT: accept() before you group_add(), or some browsers reject you.
        await self.accept()
        await self.channel_layer.group_add(self.room_name, self.channel_name)

        # Rate‐limit: no more than 5 messages per second per socket
        self.rate_limit_interval = 0.2
        self.last_message_time = 0.0

        # Increment the “participant count” for this ChatSession
        count = await self._increment_participant_count(self.session.id)
        logger.info(f"[CONNECT] user={self.current_user}, room={self.room_name}, participants={count}")

        # 1) If there are any “ended” sessions, send them first as “history” (session_range)
        past_msgs = await self._fetch_messages_from_ended_sessions(self.chatroom)
        if not past_msgs:
            # If there is absolutely no history, we send a dummy “no‐history” frame
            await self.send(
                text_data=json.dumps({
                    "history": True,
                    # we intentionally leave out "message"/"sender" so the JS will drop it.
                })
            )
        else:
            for msg in past_msgs:
                await self.send(
                    text_data=json.dumps({
                        "message":        msg.content,
                        "sender":         msg.sender.username,
                        "timestamp":      msg.timestamp.strftime("%H:%M %d/%m/%Y"),
                        "history":        True,
                        "session_range":  f"{msg.session.started_at.strftime('%H:%M %d/%m/%Y')} → "
                                          f"{msg.session.ended_at.strftime('%H:%M %d/%m/%Y')}"
                    })
                )

        # 2) Then send any backlog from the “currently open” session
        current_backlog = await self._fetch_messages_from_session(self.session)
        for msg in current_backlog:
            await self.send(
                text_data=json.dumps({
                    "message":   msg.content,
                    "sender":    msg.sender.username,
                    "timestamp": msg.timestamp.strftime("%H:%M %d/%m/%Y"),
                    "history":   False,
                })
            )

    async def receive(self, text_data):
        """
        Called whenever the browser sends a message over the WebSocket.
        We do two things:
         1) rate‐limit (no more than 5 msgs/second per socket)
         2) broadcast the sanitized message to everyone in the room (including sender)
         3) persist to the database
        """
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

        # Sanitize (strip any disallowed HTML, etc.)
        safe_message = bleach.clean(raw_message)
        timestamp_str = timezone.now().strftime("%H:%M %d/%m/%Y")

        # 1) Broadcast to the entire group (all open WebSockets in this room)
        await self.channel_layer.group_send(
            self.room_name,
            {
                "type":      "chat.message",   # Channels will look for “chat_message” below
                "message":   safe_message,
                "sender":    self.current_user,
                "history":   False,
                "timestamp": timestamp_str
            }
        )

        # 2) Persist to the database (in the background, via database_sync_to_async)
        await self._save_message(self.session, self.scope["user"], safe_message)

    async def chat_message(self, event):
        """
        This handler is invoked on *every* group_send with “type”: “chat.message”.
        We re‐package it into the same JSON shape the JS expects.
        """
        await self.send(
            text_data=json.dumps({
                "message":   event["message"],
                "sender":    event["sender"],
                "timestamp": event["timestamp"],
                "history":   event.get("history", False),
            })
        )

    async def disconnect(self, close_code):
        """
        Called when the WebSocket closes for any reason.
        We remove this channel from the group, then decrement the participant counter.
        If we were the last participant, we mark the session as ended.
        """
        if hasattr(self, "room_name"):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

            remaining = await self._decrement_participant_count(self.session.id)
            if remaining == 0:
                # Last socket left: close out that ChatSession
                await self._close_session(self.session)
            logger.info(f"[DISCONNECT] user={self.current_user}, room={self.room_name}, remaining={remaining}")

    #
    # ─── Database / ORM HELPER METHODS ───────────────────────────────────────────
    #

    @database_sync_to_async
    def _get_or_create_open_session(self, chatroom):
        open_sess = ChatSession.objects.filter(room=chatroom, ended_at__isnull=True).first()
        if open_sess:
            return open_sess
        return ChatSession.objects.create(room=chatroom)

    @database_sync_to_async
    def _close_session(self, session: ChatSession):
        session.ended_at = timezone.now()
        session.save()

    @database_sync_to_async
    def _save_message(self, session: ChatSession, user, content: str):
        ChatMessage.objects.create(session=session, sender=user, content=content)

    @database_sync_to_async
    def _fetch_messages_from_ended_sessions(self, chatroom):
        qs = ChatMessage.objects.filter(
            session__room=chatroom,
            session__ended_at__isnull=False
        ).select_related("session", "sender").order_by("session__started_at", "timestamp")
        return list(qs)

    @database_sync_to_async
    def _fetch_messages_from_session(self, session: ChatSession):
        qs = ChatMessage.objects.filter(session=session).select_related("sender").order_by("timestamp")
        return list(qs)

    @database_sync_to_async
    def _user_can_chat_with(self, user, other_username):
        # Replace this with any real authorization logic you need.
        return True

    @database_sync_to_async
    def _increment_participant_count(self, session_id: int) -> int:
        cnt = PrivateChatConsumer._session_participants.get(session_id, 0) + 1
        PrivateChatConsumer._session_participants[session_id] = cnt
        return cnt

    @database_sync_to_async
    def _decrement_participant_count(self, session_id: int) -> int:
        cnt = PrivateChatConsumer._session_participants.get(session_id, 0) - 1
        if cnt <= 0:
            # If no more sockets, drop the entry entirely
            PrivateChatConsumer._session_participants.pop(session_id, None)
            return 0
        PrivateChatConsumer._session_participants[session_id] = cnt
        return cnt
