
# chat/consumers.py
import asyncio
import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class LobbyChatConsumer(AsyncJsonWebsocketConsumer):

    ROOM_NAME_DEFAULT = "default_chat_room"

    async def connect(self):
        user = self.scope['user']
        player = await database_sync_to_async(lambda: user.player)()
        game = await database_sync_to_async(lambda: player.game)()
        if game:
            await self.send({
                'error':'player already in a game'
            })
            CLOSE_PROTOCOL_ERROR = 1002
            return await self.close(code=CLOSE_PROTOCOL_ERROR)

        await self.accept()
        await self.channel_layer.group_add(
            self.ROOM_NAME_DEFAULT, self.channel_name)

        await self.channel_layer.group_send(
            self.ROOM_NAME_DEFAULT,
            {
                "type":"chat.announcement",
                "announcement":f"{player.handle} has joined",
            })


    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.ROOM_NAME_DEFAULT, self.channel_name)
        
        user = self.scope['user']
        player = await database_sync_to_async(lambda: user.player)()
        await self.channel_layer.group_send(
            self.ROOM_NAME_DEFAULT,
            {
                "type":"chat.announcement",
                "announcement":f"{player.handle} has left",
            })

    async def receive_json(self, data):
        method = data['method']
        user = self.scope['user']
        player = await database_sync_to_async(lambda: user.player)()

        if method == 'chat.message':
            message = data['message']
            await self.channel_layer.group_send(
                self.ROOM_NAME_DEFAULT,
                {
                    "type":"chat.message",
                    "message":message,
                    "handle":player.handle,
                    "username":user.username,
                    'is_lobby_owner':user.is_superuser,
                })
        else:
            print("else?")

    async def chat_message(self, data):
        await self.send_json({
            'type':'chat.message',
            'handle':data['handle'],
            'message':data['message'],
            'isSelf': self.scope['user'].username == data['username'],
            'is_lobby_owner':data['is_lobby_owner']
        })

    async def chat_announcement(self, data):
        await self.send_json(data)


class GameLobbyChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        player = await database_sync_to_async(lambda: user.player)()
        game = await database_sync_to_async(lambda: player.game)()
        if not game:
            await self.send({
                'error':'player not in a game'
            })
            CLOSE_PROTOCOL_ERROR = 1002
            return await self.close(code=CLOSE_PROTOCOL_ERROR)

        await self.accept()
        await self.channel_layer.group_add(
            game.chat_channel_layer_name, self.channel_name)
        await self.channel_layer.group_send(
            game.chat_channel_layer_name,
            {
                "type":"chat.announcement",
                "announcement":f"{player.handle} has joined",
            })


    async def disconnect(self, close_code):
        user = self.scope['user']
        player = await database_sync_to_async(lambda: user.player)()
        game = await database_sync_to_async(lambda: player.game)()

        await self.channel_layer.group_discard(
            game.chat_channel_layer_name, self.channel_name)
        
        await self.channel_layer.group_send(
            game.chat_channel_layer_name,
            {
                "type":"chat.announcement",
                "announcement":f"{player.handle} has left",
            })

    async def receive_json(self, data):
        method = data['method']
        user = self.scope['user']
        player = await database_sync_to_async(lambda: user.player)()
        game = await database_sync_to_async(lambda: player.game)()
        if not game:
            return await self.send({'error':'user not in a game'})
            CLOSE_PROTOCOL_ERROR = 1002
            return await self.close(code=CLOSE_PROTOCOL_ERROR)

        if method == 'chat.message':
            message = data['message']
            await self.channel_layer.group_send(
                game.chat_channel_layer_name,
                {
                    "type":"chat.message",
                    "message":message,
                    "handle":player.handle,
                    "username":user.username,
                    "is_lobby_owner":player.is_lobby_owner
                })

    async def chat_message(self, data):
        await self.send_json({
            'type':'chat.message',
            'handle':data['handle'],
            'message':data['message'],
            'is_lobby_owner':data['is_lobby_owner'],
            'isSelf': self.scope['user'].username == data['username'],
        })

    async def chat_announcement(self, data):
        await self.send_json(data)


class LobbyRoomsConsumer(AsyncJsonWebsocketConsumer):

    ROOM_NAME_DEFAULT = "default_status_room"

    async def connect(self):
        user = self.scope['user']
        player = await database_sync_to_async(lambda: user.player)()
        if player.game:
            await self.send({
                'error':'player already in a game'
            })
            CLOSE_PROTOCOL_ERROR = 1002
            return await self.close(code=CLOSE_PROTOCOL_ERROR)

        await self.accept()
        await self.channel_layer.group_add(
            self.ROOM_NAME_DEFAULT, self.channel_name)


    async def disconnect(self, close_code):
        pass
        
    async def receive_json(self, data):
        pass
        
    async def room_player_count_update(self, data):
        await self.send_json(data)
    
    async def room_remove(self, data):
        await self.send_json(data)

    async def room_add(self, data):
        await self.send_json(data)
