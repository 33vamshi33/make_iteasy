import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return

        self.group_name = None
        if hasattr(self.user, 'role') and self.user.role == 'customer': # Assuming 'role' attribute exists
            self.group_name = f"customer_{self.user.id}"
        elif hasattr(self.user, 'role') and self.user.role == 'broker': # Assuming 'role' attribute exists
            self.group_name = f"broker_{self.user.id}"
        else:
            # Fallback or default group if role is not defined or different
            self.group_name = f"user_{self.user.id}"

        if self.group_name:
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
            print(f"User {self.user.id} connected to group {self.group_name}")
        else:
            await self.close()


    async def disconnect(self, close_code):
        if self.group_name:
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
            print(f"User {self.user.id} disconnected from group {self.group_name}")

    async def receive(self, text_data):
        # For now, just log received messages.
        # This can be expanded to handle client-sent messages if needed.
        print(f"Received message from {self.user.id} in group {self.group_name}: {text_data}")
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Example of echoing the message back to the sender's group
        # In a real app, you might process this message differently
        if self.group_name:
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'notification.message',
                    'message': message
                }
            )

    # Handler for messages sent to the group
    async def notification_message(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))

    # Helper method to send notifications to a group (can be called from outside the consumer)
    # This method is not directly used by the consumer itself but can be called by other parts of Django
    # e.g. from a Django signal or a view.
    # For it to be callable from synchronous Django code, it needs to be wrapped with async_to_sync
    # For now, defining it as an async method within the consumer.
    async def send_notification_to_group_internal(self, group_name, notification_data):
        """
        Sends a notification to a specific group.
        This is an example of how one might structure a method to send group messages.
        """
        await self.channel_layer.group_send(
            group_name,
            {
                'type': 'notification.message', # This will call the notification_message handler
                'message': notification_data
            }
        )

# Example of how to call send_notification_to_group_internal from synchronous code:
# from channels.layers import get_channel_layer
# from asgiref.sync import async_to_sync
#
# def some_sync_function_sending_notification(user_id, role, message):
#     channel_layer = get_channel_layer()
#     group_name = f"{role}_{user_id}" # Construct the group name
#     async_to_sync(channel_layer.group_send)(
#         group_name,
#         {
#             "type": "notification.message",
#             "message": message,
#         }
#     )
#
# Example usage:
# some_sync_function_sending_notification(user_id=1, role='customer', message="Your order has been updated.")
