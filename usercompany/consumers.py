"""
WebSocket consumers for Company users.

This module handles real-time WebSocket connections for:
- Real-time notifications for companies
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications for companies.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        # Verify user is authenticated and is empresa
        if not self.scope["user"].is_authenticated:
            await self.close()
            return

        if not await self.is_empresa_user():
            await self.close()
            return

        self.user_id = self.scope["user"].id
        self.room_group_name = f'notifications_empresa_{self.user_id}'

        # Join notification group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send unread count
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave notification group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Receive message from WebSocket."""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', '')

            if message_type == 'mark_as_read':
                notification_id = text_data_json.get('notification_id')
                if notification_id:
                    await self.mark_notification_as_read(notification_id)
            elif message_type == 'mark_all_as_read':
                await self.mark_all_notifications_as_read()
            elif message_type == 'delete':
                notification_id = text_data_json.get('notification_id')
                if notification_id:
                    await self.delete_notification(notification_id)
        except json.JSONDecodeError:
            pass

    async def notification_message(self, event):
        """Send notification to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))

    async def unread_count_update(self, event):
        """Send updated unread count to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': event['count']
        }))

    @database_sync_to_async
    def is_empresa_user(self) -> bool:
        """Check if user is empresa."""
        return self.scope['user'].is_empresa()

    @database_sync_to_async
    def get_unread_count(self) -> int:
        """Get count of unread notifications."""
        from usercompany.models import NotificacaoEmpresa
        from core.models import Empresa

        empresa = Empresa.objects.filter(user=self.scope['user']).first()
        if not empresa:
            return 0

        return NotificacaoEmpresa.objects.filter(
            empresa=empresa,
            lida=False
        ).count()

    @database_sync_to_async
    def mark_notification_as_read(self, notification_id: int):
        """Mark a notification as read."""
        from usercompany.models import NotificacaoEmpresa
        from core.models import Empresa

        empresa = Empresa.objects.filter(user=self.scope['user']).first()
        if not empresa:
            return

        NotificacaoEmpresa.objects.filter(
            id=notification_id,
            empresa=empresa
        ).update(lida=True)

    @database_sync_to_async
    def mark_all_notifications_as_read(self):
        """Mark all notifications as read."""
        from usercompany.models import NotificacaoEmpresa
        from core.models import Empresa

        empresa = Empresa.objects.filter(user=self.scope['user']).first()
        if not empresa:
            return

        NotificacaoEmpresa.objects.filter(
            empresa=empresa,
            lida=False
        ).update(lida=True)

    @database_sync_to_async
    def delete_notification(self, notification_id: int):
        """Delete a notification."""
        from usercompany.models import NotificacaoEmpresa
        from core.models import Empresa

        empresa = Empresa.objects.filter(user=self.scope['user']).first()
        if not empresa:
            return

        NotificacaoEmpresa.objects.filter(
            id=notification_id,
            empresa=empresa
        ).delete()
