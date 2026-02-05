import json
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import ChatRoom, ChatMessage, User


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time chat."""
    
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.group_name = f"chat_{self.room_id}"
        
        query_string = self.scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        self.jwt_token = params.get('token', [None])[0]
        self.visitor_token = params.get('visitor', [None])[0]
        
        self.user = await self._get_user_from_token(self.jwt_token)
        if not self.user:
            scope_user = self.scope.get('user')
            if scope_user and scope_user.is_authenticated:
                self.user = scope_user
        self.room = await self._get_room(self.room_id)
        
        if not self.room:
            await self.close(code=4404)
            return
        
        is_allowed = await self._is_allowed(self.room, self.user, self.visitor_token)
        if not is_allowed:
            await self.close(code=4403)
            return
        
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
    
    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
    
    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return
        
        message = (data.get('message') or '').strip()
        if not message:
            return
        
        sender_type = 'visitor'
        sender_user = None
        if self.user and self.user.is_authenticated and self.user == self.room.owner:
            sender_type = 'owner'
            sender_user = self.user
        
        msg = await self._create_message(self.room, sender_type, sender_user, message)
        
        payload = {
            'id': str(msg.id),
            'room_id': str(self.room.id),
            'sender_type': sender_type,
            'message': msg.content,
            'created_at': msg.created_at.isoformat(),
        }
        
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'chat.message',
                'payload': payload,
            }
        )
    
    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event['payload']))
    
    @database_sync_to_async
    def _get_room(self, room_id):
        return ChatRoom.objects.filter(id=room_id, is_active=True).select_related('owner').first()
    
    @database_sync_to_async
    def _get_user_from_token(self, token):
        if not token:
            return None
        try:
            access = AccessToken(token)
            user_id = access.get('user_id')
            if not user_id:
                return None
            return User.objects.get(id=user_id)
        except (TokenError, User.DoesNotExist):
            return None
    
    @database_sync_to_async
    def _create_message(self, room, sender_type, sender_user, content):
        msg = ChatMessage.objects.create(
            room=room,
            sender_type=sender_type,
            sender=sender_user,
            content=content,
        )
        room.save(update_fields=['updated_at'])
        return msg
    
    @database_sync_to_async
    def _is_allowed(self, room, user, visitor_token):
        if user and user.is_authenticated and user == room.owner:
            return True
        if visitor_token and str(room.visitor_token) == str(visitor_token):
            return True
        return False
