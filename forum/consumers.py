from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
import json
import logging

logger = logging.getLogger(__name__)

class PrivateChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.other_user = self.scope["url_route"]["kwargs"]["username"]

        # Fix: safely access session key
        self.current_user = await sync_to_async(self.get_username)()
        self.user = self.current_user

        a, b = sorted([self.current_user, self.other_user.lower()])
        self.room_name = f"private_chat_{a}_{b}"

        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    def get_username(self):
        return self.scope["session"].get("Username", "guest").lower()


    async def disconnect(self, close_code):
        if hasattr(self, "room_name"):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)
        logger.info(f"[DISCONNECT] user={self.user}, room={getattr(self, 'room_name', 'N/A')}")

    async def receive(self, text_data):
        data = json.loads(text_data)
        logger.info(f"[GROUP_SEND] room={self.room_name}, from={self.current_user}, msg={data['message']}")
        await self.channel_layer.group_send(
            self.room_name,
            {
                "type": "chat_message",
                "message": data["message"],
                "sender": self.current_user,
            }
        )

    async def chat_message(self, event):
        logger.info(f"[SEND] to={self.channel_name}, message={event}")
        await self.send(text_data=json.dumps({
            "message": event["message"],
            "sender": event["sender"],
        }))
