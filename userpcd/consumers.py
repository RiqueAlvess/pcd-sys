"""
WebSocket consumers for PCD users.

This module handles real-time WebSocket connections for:
- Chat between approved candidates and companies
- Real-time notifications for PCDs
"""

import json
from typing import Any, Dict
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat between PCDs and companies.

    Only allows chat for approved candidates (status='aprovado').
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        # Verify user is authenticated
        if not self.scope["user"].is_authenticated:
            await self.close()
            return

        # Verify user has permission to access this chat room
        has_permission = await self.check_chat_permission()
        if not has_permission:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send chat history
        await self.send_chat_history()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Receive message from WebSocket."""
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json.get('message', '')
            message_type = text_data_json.get('type', 'chat_message')

            if message_type == 'chat_message' and message.strip():
                # Save message to database
                saved_message = await self.save_message(message)

                # Send message to room group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': saved_message['conteudo'],
                        'sender': saved_message['sender'],
                        'timestamp': saved_message['timestamp'],
                        'is_empresa': saved_message['is_empresa'],
                    }
                )
            elif message_type == 'mark_as_read':
                # Mark messages as read
                await self.mark_messages_as_read()
        except json.JSONDecodeError:
            pass

    async def chat_message(self, event):
        """Send message to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender': event['sender'],
            'timestamp': event['timestamp'],
            'is_empresa': event['is_empresa'],
        }))

    @database_sync_to_async
    def check_chat_permission(self) -> bool:
        """
        Check if user has permission to access this chat room.

        Room name format: 'pcd_{pcd_id}_empresa_{empresa_id}_vaga_{vaga_id}'
        """
        from userpcd.models import Conversa, Candidatura
        from core.models import PCDProfile, Empresa

        try:
            # Parse room name
            parts = self.room_name.split('_')
            if len(parts) != 6:
                return False

            pcd_id = int(parts[1])
            empresa_id = int(parts[3])
            vaga_id = int(parts[5])

            user = self.scope['user']

            # Check if user is PCD or Empresa involved in this conversation
            if user.is_pcd():
                pcd_profile = PCDProfile.objects.filter(user=user, id=pcd_id).first()
                if not pcd_profile:
                    return False
            elif user.is_empresa():
                empresa = Empresa.objects.filter(user=user, id=empresa_id).first()
                if not empresa:
                    return False
            else:
                return False

            # Check if there's an approved candidatura
            candidatura = Candidatura.objects.filter(
                pcd_id=pcd_id,
                vaga_id=vaga_id,
                status='aprovado'
            ).first()

            if not candidatura:
                return False

            # Get or create conversation
            conversa, created = Conversa.objects.get_or_create(
                pcd_id=pcd_id,
                empresa_id=empresa_id,
                vaga_id=vaga_id,
                candidatura=candidatura
            )

            return True
        except (ValueError, IndexError):
            return False

    @database_sync_to_async
    def save_message(self, message: str) -> Dict[str, Any]:
        """Save message to database."""
        from userpcd.models import Conversa, Mensagem
        from django.utils import timezone

        # Parse room name
        parts = self.room_name.split('_')
        pcd_id = int(parts[1])
        empresa_id = int(parts[3])
        vaga_id = int(parts[5])

        # Get conversation
        conversa = Conversa.objects.get(
            pcd_id=pcd_id,
            empresa_id=empresa_id,
            vaga_id=vaga_id
        )

        # Determine if sender is empresa
        user = self.scope['user']
        is_empresa = user.is_empresa()

        # Create message
        mensagem = Mensagem.objects.create(
            conversa=conversa,
            remetente_empresa=is_empresa,
            conteudo=message,
            lida=False
        )

        return {
            'conteudo': mensagem.conteudo,
            'sender': user.email,
            'timestamp': mensagem.enviada_em.isoformat(),
            'is_empresa': is_empresa,
        }

    @database_sync_to_async
    def send_chat_history(self):
        """Send chat history to the newly connected user."""
        from userpcd.models import Conversa

        # Parse room name
        parts = self.room_name.split('_')
        pcd_id = int(parts[1])
        empresa_id = int(parts[3])
        vaga_id = int(parts[5])

        # Get conversation
        conversa = Conversa.objects.filter(
            pcd_id=pcd_id,
            empresa_id=empresa_id,
            vaga_id=vaga_id
        ).first()

        if not conversa:
            return

        # Get messages
        messages = conversa.mensagem_set.all().order_by('enviada_em')[:50]

        return [
            {
                'conteudo': msg.conteudo,
                'sender': 'Empresa' if msg.remetente_empresa else 'PCD',
                'timestamp': msg.enviada_em.isoformat(),
                'is_empresa': msg.remetente_empresa,
                'lida': msg.lida,
            }
            for msg in messages
        ]

    @database_sync_to_async
    def mark_messages_as_read(self):
        """Mark all unread messages as read for current user."""
        from userpcd.models import Conversa

        # Parse room name
        parts = self.room_name.split('_')
        pcd_id = int(parts[1])
        empresa_id = int(parts[3])
        vaga_id = int(parts[5])

        # Get conversation
        conversa = Conversa.objects.filter(
            pcd_id=pcd_id,
            empresa_id=empresa_id,
            vaga_id=vaga_id
        ).first()

        if not conversa:
            return

        user = self.scope['user']
        is_empresa = user.is_empresa()

        # Mark messages as read
        if is_empresa:
            # Mark PCD messages as read
            conversa.mensagem_set.filter(
                remetente_empresa=False,
                lida=False
            ).update(lida=True)
        else:
            # Mark empresa messages as read
            conversa.mensagem_set.filter(
                remetente_empresa=True,
                lida=False
            ).update(lida=True)


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications for PCDs.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        # Verify user is authenticated and is PCD
        if not self.scope["user"].is_authenticated:
            await self.close()
            return

        if not await self.is_pcd_user():
            await self.close()
            return

        self.user_id = self.scope["user"].id
        self.room_group_name = f'notifications_pcd_{self.user_id}'

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
    def is_pcd_user(self) -> bool:
        """Check if user is PCD."""
        return self.scope['user'].is_pcd()

    @database_sync_to_async
    def get_unread_count(self) -> int:
        """Get count of unread notifications."""
        from userpcd.models import Notificacao
        return Notificacao.objects.filter(
            user=self.scope['user'],
            lida=False
        ).count()

    @database_sync_to_async
    def mark_notification_as_read(self, notification_id: int):
        """Mark a notification as read."""
        from userpcd.models import Notificacao

        Notificacao.objects.filter(
            id=notification_id,
            user=self.scope['user']
        ).update(lida=True)

    @database_sync_to_async
    def mark_all_notifications_as_read(self):
        """Mark all notifications as read."""
        from userpcd.models import Notificacao

        Notificacao.objects.filter(
            user=self.scope['user'],
            lida=False
        ).update(lida=True)

    @database_sync_to_async
    def delete_notification(self, notification_id: int):
        """Delete a notification."""
        from userpcd.models import Notificacao

        Notificacao.objects.filter(
            id=notification_id,
            user=self.scope['user']
        ).delete()
