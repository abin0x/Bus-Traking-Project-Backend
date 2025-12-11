import json
from channels.generic.websocket import AsyncWebsocketConsumer

class BusTrackingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("tracking_group", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("tracking_group", self.channel_name)

    async def send_update(self, event):
        message = event['message']
        await self.send(text_data=json.dumps(message))