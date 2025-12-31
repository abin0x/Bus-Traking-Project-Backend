
# import json
# from channels.generic.websocket import AsyncWebsocketConsumer
# from channels.exceptions import StopConsumer

# class BusTrackingConsumer(AsyncWebsocketConsumer):
#     ROOM_GROUP_NAME = "tracking_group"

#     async def connect(self):
#         try:
#             await self.channel_layer.group_add(
#                 self.ROOM_GROUP_NAME,
#                 self.channel_name
#             )
#             await self.accept()
#             print(f"✅ WebSocket Connected: {self.channel_name}")
#             await self.send(text_data=json.dumps({
#                 "status": "connected",
#                 "message": "Live tracking stream started."
#             }))

#         except Exception as e:
#             print(f"❌ Connection Error: {e}")
#             await self.close()

#     async def disconnect(self, close_code):
#         print(f"⚠️ WebSocket Disconnected: {self.channel_name} | Code: {close_code}")
#         await self.channel_layer.group_discard(
#             self.ROOM_GROUP_NAME,
#             self.channel_name
#         )
#         raise StopConsumer()

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import StopConsumer

class BusTrackingConsumer(AsyncWebsocketConsumer):
    ROOM_GROUP_NAME = "tracking_group"

    async def connect(self):
        # ১. ইউজার অথেন্টিকেশন চেক (সেশন থেকে ডিজেঙ্গো এটি অটোমেটিক স্কোপে দেয়)
        self.user = self.scope["user"]

        # ২. ইউজার লগইন করা আছে কি না এবং ভেরিফাইড কি না তা চেক করা
        if self.user.is_authenticated and self.user.is_verified:
            try:
                await self.channel_layer.group_add(
                    self.ROOM_GROUP_NAME,
                    self.channel_name
                )
                await self.accept()
                print(f"✅ Secure WebSocket Connected: {self.user.student_id}")
                
                await self.send(text_data=json.dumps({
                    "status": "connected",
                    "message": f"Welcome {self.user.full_name}! Live tracking started."
                }))

            except Exception as e:
                print(f"❌ Connection Error: {e}")
                await self.close()
        else:
            # ৩. যদি ইউজার লগইন করা না থাকে বা ভেরিফাইড না হয়, কানেকশন রিজেক্ট করা
            print(f"🚫 Unauthorized Connection Attempt Refused.")
            await self.close()

    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            await self.channel_layer.group_discard(
                self.ROOM_GROUP_NAME,
                self.channel_name
            )
        raise StopConsumer()


    async def send_update(self, event):
        try:
            message = event['message']
            await self.send(text_data=json.dumps(message))
            
        except Exception as e:
            print(f"❌ Error sending data: {e}")