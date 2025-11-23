import json
import jwt
from django.conf import settings
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from apps.user.models import User  # 修正导入路径
from .models import Chat
from .services import ChatService


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """WebSocket连接建立"""
        self.user = None
        self.room_group_name = None

        # 验证token
        token = self.scope['url_route']['kwargs'].get('token')
        if not token:
            await self.close()
            return

        try:
            # 验证JWT token
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user_openid = payload.get('openid')

            if user_openid:
                self.user = await self.get_user(user_openid)
                if self.user:
                    self.room_group_name = f'user_{user_openid}'

                    # 加入用户个人的房间组
                    await self.channel_layer.group_add(
                        self.room_group_name,
                        self.channel_name
                    )

                    # 更新在线状态
                    await self.update_online_status(True)

                    await self.accept()
                    return

        except jwt.ExpiredSignatureError:
            pass
        except jwt.InvalidTokenError:
            pass

        await self.close()

    async def disconnect(self, close_code):
        """WebSocket连接断开"""
        if self.user and self.room_group_name:
            # 离开房间组
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

            # 更新离线状态
            await self.update_online_status(False)

    async def receive(self, text_data):
        """接收WebSocket消息"""
        if not self.user:
            return

        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing':
                await self.handle_typing_indicator(data)
            elif message_type == 'read_receipt':
                await self.handle_read_receipt(data)

        except json.JSONDecodeError:
            await self.send_error('无效的JSON数据')

    async def handle_chat_message(self, data):
        """处理聊天消息"""
        receiver_openid = data.get('receiver')
        msg_type = data.get('msg_type', 'text')
        msg_content = data.get('msg_content', '')

        if not receiver_openid or not msg_content:
            await self.send_error('缺少必要参数')
            return

        try:
            # 发送消息
            message = await self.send_message_async(
                self.user, receiver_openid, msg_type, msg_content
            )

            # 发送给接收者
            await self.channel_layer.group_send(
                f'user_{receiver_openid}',
                {
                    'type': 'chat_message',
                    'message': await self.serialize_message_async(message)
                }
            )

            # 发送回发送者（确认发送成功）
            await self.send(text_data=json.dumps({
                'type': 'message_sent',
                'message': await self.serialize_message_async(message)
            }))

        except Exception as e:
            await self.send_error(str(e))

    async def handle_typing_indicator(self, data):
        """处理输入指示器"""
        receiver_openid = data.get('receiver')
        is_typing = data.get('is_typing', False)

        if receiver_openid:
            await self.channel_layer.group_send(
                f'user_{receiver_openid}',
                {
                    'type': 'typing_indicator',
                    'sender': self.user.openid,
                    'is_typing': is_typing
                }
            )

    async def handle_read_receipt(self, data):
        """处理已读回执"""
        message_id = data.get('message_id')
        if message_id:
            await self.mark_message_read_async(message_id, self.user)

    async def chat_message(self, event):
        """接收聊天消息"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))

    async def typing_indicator(self, event):
        """接收输入指示器"""
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'sender': event['sender'],
            'is_typing': event['is_typing']
        }))

    async def send_error(self, error_message):
        """发送错误消息"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': error_message
        }))

    @database_sync_to_async
    def get_user(self, openid):
        """获取用户"""
        try:
            return User.objects.get(openid=openid)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def send_message_async(self, sender, receiver_openid, msg_type, msg_content):
        """异步发送消息"""
        try:
            receiver = User.objects.get(openid=receiver_openid)
            return ChatService.send_message(sender, receiver, msg_type, msg_content)
        except User.DoesNotExist:
            raise ValueError("接收用户不存在")
        except ValueError as e:
            raise e

    @database_sync_to_async
    def serialize_message_async(self, message):
        """异步序列化消息"""
        from .serializers import ChatSerializer

        # 创建一个简单的字典来避免序列化器依赖
        return {
            'id': message.id,
            'sender_openid': message.sender_openid.openid,
            'sender_info': {
                'openid': message.sender_openid.openid,
                'nickname': message.sender_openid.nickname,
                'avatar_url': message.sender_openid.avatar_url
            },
            'receiver_openid': message.receiver_openid.openid,
            'receiver_info': {
                'openid': message.receiver_openid.openid,
                'nickname': message.receiver_openid.nickname,
                'avatar_url': message.receiver_openid.avatar_url
            },
            'msg_type': message.msg_type,
            'msg_content': message.msg_content,
            'send_time': message.send_time.isoformat(),
            'read_status': message.read_status,
            'message_summary': message.get_message_summary()
        }

    @database_sync_to_async
    def mark_message_read_async(self, message_id, user):
        """异步标记消息为已读"""
        try:
            message = Chat.objects.get(id=message_id, receiver_openid=user)
            message.mark_as_read()
        except Chat.DoesNotExist:
            pass

    @database_sync_to_async
    def update_online_status(self, is_online):
        """异步更新在线状态"""
        ChatService.update_user_online_status(self.user, is_online)