
# chat/consumers.py
import asyncio
import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class ConnectQuatroConsumer(AsyncJsonWebsocketConsumer):

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
            game.channel_layer_name, self.channel_name)

    async def disconnect(self, close_code):
        pass


    async def receive_json(self, data):
        pass


    async def player_quit(self, data):
        await self.send_json(data)


    async def player_joined(self, data):
        await self.send_json(data)

    async def game_started(self, data):
        await self.send_json(data)
    
    async def game_move(self, data):
        user = self.scope['user']
        player = await database_sync_to_async(lambda: user.player)()
        game_state = data['game_state']
        
        if 'next_player_slug' in game_state:
            data['game_state']['active_player'] = player.slug == game_state['next_player_slug']
        
        if game_state['winner']:
            data['game_state']['player_won'] = game_state['winner']['slug'] == player.slug
        
        await self.send_json(data)

    async def player_promoted(self, data):
        await self.send_json(data)
