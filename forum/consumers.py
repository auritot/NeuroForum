# forum/consumers.py
import json
import time
import bleach
import logging
import asyncio

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from pytz import timezone as pytz_timezone
from forum.crypto_utils import decrypt_message

from django.contrib.auth import get_user_model
from .models import ChatRoom, ChatSession, ChatMessage, UserAccount

logger = logging.getLogger(__name__)
User = get_user_model()


class PrivateChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for a private chat between two users.
    """

    # In-memory count of open sockets per ChatSession
    _session_participants = {}

    async def connect(self):
        """
        Called when a websocket client connects.
        - Rejects if not authenticated or chatting with self.
        - Joins:
          1) the chat-room group for broadcasting actual chat messages
          2) a personal notify_<username> group for unread‐ping notifications
        - Sends any previous‐session history, then backlog in current session.
        """
        user = self.scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            await self.close(code=4001)
            return

        self.other_user = self.scope["url_route"]["kwargs"]["username"].lower()
        self.current_user = user.Username.lower()
        if self.current_user == self.other_user:
            await self.close(code=4004)
            return

        # canonical room name
        a, b = sorted([self.current_user, self.other_user])
        self.room_name = f"private_{a}_{b}"
        self.chatroom = await database_sync_to_async(ChatRoom.get_or_create_private)(a, b)
        self.session = await self._get_or_create_open_session(self.chatroom)

        # # clear unread count for me in this room
        # await self._mark_as_read(self.scope["user"], self.chatroom)

        # first accept, then group_add
        await self.accept()
        # join my personal notify channel
        await self.channel_layer.group_add(f"notify_{self.current_user}", self.channel_name)
        # join the shared chat room
        await self.channel_layer.group_add(self.room_name, self.channel_name)

        # rate‐limit setup
        self.rate_limit_interval = 0.2
        self.last_message_time = 0.0

        # track number of participants
        await self._increment_participant_count(self.session.id)

        # 1) send ended‐session history
        past_msgs = await self._fetch_messages_from_ended_sessions(self.chatroom)
        sg = pytz_timezone("Asia/Singapore")
        if not past_msgs:
            await self.send(text_data=json.dumps({"history": True}))
        else:
            for msg in past_msgs:
                local_time = msg.timestamp.astimezone(sg)
                await self.send(text_data=json.dumps({
                    "message":        msg.content,
                    "sender":         msg.sender.Username,
                    "timestamp":      local_time.strftime("%I:%M %p %d/%m/%Y"),
                    "history":        True,
                    "session_range":  f"{msg.session.started_at.astimezone(sg).strftime('%I:%M %p %d/%m/%Y')} → {msg.session.ended_at.astimezone(sg).strftime('%I:%M %p %d/%m/%Y')}"
                }))

        # 2) send backlog from the currently open session
        current_backlog = await self._fetch_messages_from_session(self.session)
        for msg in current_backlog:
            local_time = msg.timestamp.astimezone(sg)
            await self.send(text_data=json.dumps({
                "message":   msg.content,
                "sender":    msg.sender.Username,
                "timestamp": local_time.strftime("%I:%M %p %d/%m/%Y"),
                "history":   False,
            }))

    async def receive(self, text_data):
        """
        Called when a text frame is received.
        - Broadcasts the cleaned message to the room.
        - Saves it to DB.
        - Then pings the other user’s personal notify_<other> group.
        """
        now = time.time()
        if now - self.last_message_time < self.rate_limit_interval:
            return
        self.last_message_time = now

        data = json.loads(text_data)
        raw = data.get("message", "")
        if not isinstance(raw, str) or len(raw) > 2048:
            return

        safe_message = bleach.clean(raw)
        sg = timezone.now().astimezone(pytz_timezone("Asia/Singapore"))
        timestamp_str = sg.strftime("%I:%M %p %d/%m/%Y")

        # persist and retrieve the saved message
        saved_msg = await self._save_message(self.session, self.scope["user"], safe_message)
        room_name = saved_msg.session.room.name

        try:
            decrypted_content = decrypt_message(saved_msg.content_encrypted, room_name)
        except Exception as e:
            print("❌ DECRYPTION ERROR:", str(e))
            decrypted_content = "[Decryption Failed]"

        # broadcast the decrypted version
        await self.channel_layer.group_send(
            self.room_name,
            {
                "type":      "chat.message",
                "message":   decrypted_content,
                "sender":    self.current_user,
                "timestamp": timestamp_str,
                "history":   False,
            }
        )

    async def chat_message(self, event):
        """
        Handler for actual chat messages coming from the room group.
        Repackages them into the JSON shape the JS expects.
        """
        await self.send(text_data=json.dumps({
            "message":   event["message"],
            "sender":    event["sender"],
            "timestamp": event["timestamp"],
            "history":   event.get("history", False),
        }))

    async def chat_unread_notification(self, event):
        """
        Handler for unread‐notification pings.
        Instead of a chat bubble, we forward a {type:"notify",from:…} frame
        so the frontend can bump badges and glow the icon.
        """
        await self.send(text_data=json.dumps({
            "type": "notify",
            "from": event["from_user"],
        }))

    async def disconnect(self, close_code):
        """
        Clean up group memberships and close session if needed.
        """
        if hasattr(self, "room_name"):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)
            await self.channel_layer.group_discard(f"notify_{self.current_user}", self.channel_name)
            remaining = await self._decrement_participant_count(self.session.id)
            if remaining == 0:
                await self._close_session(self.session)

    # ────────────────────────────────────────────────────────────────────────
    # Database/ORM helpers
    # ────────────────────────────────────────────────────────────────────────

    @database_sync_to_async
    def _get_or_create_open_session(self, chatroom):
        open_sess = ChatSession.objects.filter(room=chatroom, ended_at__isnull=True).first()
        if open_sess:
            return open_sess
        return ChatSession.objects.create(room=chatroom)

    @database_sync_to_async
    def _close_session(self, session):
        session.ended_at = timezone.now()
        session.save()

    @database_sync_to_async
    def _save_message(self, session, user, content):
        msg = ChatMessage.objects.create(session=session, sender=user, content=content)

    @database_sync_to_async
    def _fetch_messages_from_ended_sessions(self, chatroom):
        qs = ChatMessage.objects.filter(
            session__room=chatroom, session__ended_at__isnull=False
        ).select_related("session", "sender").order_by("session__started_at", "timestamp")
        return list(qs)

    @database_sync_to_async
    def _fetch_messages_from_session(self, session):
        qs = ChatMessage.objects.filter(session=session).select_related("sender").order_by("timestamp")
        return list(qs)

    @database_sync_to_async
    def _user_can_chat_with(self, user, other_username):
        return True

    @database_sync_to_async
    def _increment_participant_count(self, session_id):
        cnt = PrivateChatConsumer._session_participants.get(session_id, 0) + 1
        PrivateChatConsumer._session_participants[session_id] = cnt
        return cnt

    @database_sync_to_async
    def _decrement_participant_count(self, session_id):
        cnt = PrivateChatConsumer._session_participants.get(session_id, 0) - 1
        if cnt <= 0:
            PrivateChatConsumer._session_participants.pop(session_id, None)
            return 0
        PrivateChatConsumer._session_participants[session_id] = cnt
        return cnt

    # @database_sync_to_async
    # def _mark_as_read(self, user, room):
    #     ChatUnread.objects.filter(user=user, room=room).update(unread_count=0)
    @database_sync_to_async
    def _get_latest_decrypted_content(self, session, user):
        msg = ChatMessage.objects.filter(session=session, sender=user).order_by("-timestamp").first()
        if msg:
            try:
                room_name = msg.session.room.name
                return decrypt_message(msg.content_encrypted, room_name)
            except Exception as e:
                print("❌ DECRYPT ERROR:", str(e))
                return "[Decryption Failed]"
        return "[Decryption Failed]"
    
    @database_sync_to_async
    def _save_message(self, session, user, content):
        msg = ChatMessage(session=session, sender=user)
        msg.content = content  # triggers encryption
        msg.save()
        return msg