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

from django.contrib.auth import get_user_model
from .models import ChatRoom, ChatSession, ChatMessage, ChatUnread, UserAccount

logger = logging.getLogger(__name__)
User = get_user_model()


class PrivateChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for a two‐way private chat.
    URL: /ws/chat/<other_username>/
    """
    _session_participants = {}

    async def connect(self):
        user = self.scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            await self.close(code=4001)
            return

        self.other_user = self.scope["url_route"]["kwargs"]["username"].lower()
        self.current_user = user.Username.lower()

        if self.current_user == self.other_user:
            await self.close(code=4004)
            return

        # Canonical room name
        a, b = sorted([self.current_user, self.other_user])
        self.room_name = f"private_{a}_{b}"

        # Fetch/Create room & session
        self.chatroom = await database_sync_to_async(ChatRoom.get_or_create_private)(a, b)
        self.session = await self._get_or_create_open_session(self.chatroom)

        if not await self._user_can_chat_with(self.scope["user"], self.other_user):
            await self.close(code=4003)
            return

        # Reset unread counter when joining
        await self._mark_as_read(self.scope["user"], self.chatroom)

        # IMPORTANT: accept before group_add
        await self.accept()

        # Join the chat room group
        await self.channel_layer.group_add(self.room_name, self.channel_name)

        # ALSO join your own notification group so you can receive unread pings
        await self.channel_layer.group_add(f"notify_{self.current_user}", self.channel_name)

        # Rate‐limit setup
        self.rate_limit_interval = 0.2
        self.last_message_time = 0.0

        # Track session participants
        await self._increment_participant_count(self.session.id)

        # Send history from ended sessions...
        past_msgs = await self._fetch_messages_from_ended_sessions(self.chatroom)
        if not past_msgs:
            await self.send(text_data=json.dumps({"history": True}))
        else:
            sg = pytz_timezone("Asia/Singapore")
            for msg in past_msgs:
                local_time = msg.timestamp.astimezone(sg)
                await self.send(text_data=json.dumps({
                    "message":        msg.content,
                    "sender":         msg.sender.Username,
                    "timestamp":      local_time.strftime("%I:%M %p %d/%m/%Y"),
                    "history":        True,
                    "session_range":  f"{msg.session.started_at.astimezone(sg).strftime('%I:%M %p %d/%m/%Y')} → "
                                      f"{msg.session.ended_at.astimezone(sg).strftime('%I:%M %p %d/%m/%Y')}"
                }))

        # ...then backlog from the open session
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
        now = time.time()
        if now - self.last_message_time < self.rate_limit_interval:
            return
        self.last_message_time = now

        try:
            data = json.loads(text_data)
            raw_message = data.get("message", "")
            if not isinstance(raw_message, str) or len(raw_message) > 2048:
                return

            safe_message = bleach.clean(raw_message)
            singapore_time = timezone.now().astimezone(pytz_timezone("Asia/Singapore"))
            timestamp_str = singapore_time.strftime("%I:%M %p %d/%m/%Y")

            # 1) Broadcast to the chat room
            await self.channel_layer.group_send(
                self.room_name,
                {
                    "type":      "chat.message",
                    "message":   safe_message,
                    "sender":    self.current_user,
                    "history":   False,
                    "timestamp": timestamp_str,
                }
            )

            # 2) Persist it
            await self._save_message(self.session, self.scope["user"], safe_message)

            # 3) Tell *only* the other user that they have a new unread message
            await self.channel_layer.group_send(
                f"notify_{self.other_user}",
                {
                    "type":      "chat.unread_notification",
                    "from_user": self.current_user,
                }
            )

        except Exception as e:
            logger.error("❌ WebSocket receive() crashed:\n" + traceback.format_exc())
            await self.close(code=1011)


    async def chat_message(self, event):
        # Repackage for the JS client
        await self.send(text_data=json.dumps({
            "message":   event["message"],
            "sender":    event["sender"],
            "timestamp": event["timestamp"],
            "history":   event.get("history", False),
        }))


    async def chat_unread_notification(self, event):
        # Sent only to the other user when you call group_send(..., type="chat.unread_notification")
        await self.send(text_data=json.dumps({
            "type":     "notify",
            "from":     event["from_user"],
        }))


    async def disconnect(self, close_code):
        # Clean up group memberships & session tracking
        if hasattr(self, "room_name"):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)
            await self.channel_layer.group_discard(f"notify_{self.current_user}", self.channel_name)
            remaining = await self._decrement_participant_count(self.session.id)
            if remaining == 0:
                await self._close_session(self.session)

    async def chat_unread_notification(self, event):
        await self.send(text_data=json.dumps({
            "type": "notify",
            "from": event["from_user"],
        }))


    # ───── Database / ORM helpers ─────

    @database_sync_to_async
    def _get_or_create_open_session(self, chatroom):
        open_sess = ChatSession.objects.filter(room=chatroom, ended_at__isnull=True).first()
        return open_sess or ChatSession.objects.create(room=chatroom)

    @database_sync_to_async
    def _close_session(self, session):
        session.ended_at = timezone.now()
        session.save()

    @database_sync_to_async
    def _save_message(self, session, user, content):
        ChatMessage.objects.create(session=session, sender=user, content=content)

        # also increment the DB‐driven unread counter
        participants = self.chatroom.name.replace("private_", "").split("_")
        other = [u for u in participants if u != user.Username.lower()]
        if other:
            recipient = UserAccount.objects.get(Username__iexact=other[0])
            unread_obj, _ = ChatUnread.objects.get_or_create(user=recipient, room=self.chatroom)
            unread_obj.unread_count += 1
            unread_obj.save()

    @database_sync_to_async
    def _fetch_messages_from_ended_sessions(self, chatroom):
        return list(ChatMessage.objects.filter(
            session__room=chatroom, session__ended_at__isnull=False
        ).select_related("session","sender").order_by("session__started_at","timestamp"))

    @database_sync_to_async
    def _fetch_messages_from_session(self, session):
        return list(ChatMessage.objects.filter(
            session=session
        ).select_related("sender").order_by("timestamp"))

    @database_sync_to_async
    def _user_can_chat_with(self, user, other_username):
        return True  # your authorization logic

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

    @database_sync_to_async
    def _mark_as_read(self, user, room):
        ChatUnread.objects.filter(user=user, room=room).update(unread_count=0)

