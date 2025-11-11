"""
WebSocket URL routing configuration for the PCD System.

This module defines WebSocket URL patterns for real-time features:
- Chat between approved candidates and companies
- Real-time notifications for both PCDs and companies
"""

from django.urls import re_path
from userpcd import consumers as pcd_consumers
from usercompany import consumers as company_consumers

websocket_urlpatterns = [
    # Chat WebSocket endpoints
    re_path(r'ws/chat/(?P<room_name>[\w-]+)/$', pcd_consumers.ChatConsumer.as_asgi()),

    # PCD Notifications WebSocket
    re_path(r'ws/notifications/pcd/$', pcd_consumers.NotificationConsumer.as_asgi()),

    # Company Notifications WebSocket
    re_path(r'ws/notifications/company/$', company_consumers.NotificationConsumer.as_asgi()),
]
