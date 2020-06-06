
import uuid
import random

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from lobby.consumers import LobbyRoomsConsumer
from lobby.models import Game
from connectquatro.models import Board
from connectquatro import lib as cq_lib


def new_join_game_id() -> str:
    while True:
        new_id = str(uuid.uuid4()).replace("-", "")
        if not Game.objects.filter(join_game_id=new_id).exists():
            return new_id

# sync database functions

@transaction.atomic
def player_create_connectquat_lobby(
    player, game_name:str, board_length_x:int, board_length_y:int, 
    max_players:int, max_to_win:int, max_seconds_per_turn:int, is_public=True):

    game = Game.objects.create(
        game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT,
        name=game_name, max_players=max_players,
        is_public=is_public, is_started=False,
        max_seconds_per_turn=max_seconds_per_turn,
        join_game_id=new_join_game_id())

    board = Board.objects.create(
        game=game, max_to_win=max_to_win,
        board_length_x=board_length_x, board_length_y=board_length_y)

    player.game = game
    player.is_lobby_owner = True
    player.save(update_fields=['game', 'is_lobby_owner'])

    if is_public:
        update_lobby_list_add_connect_quatro(game, board)

    return game

@transaction.atomic
def player_join_lobby(player, game):
    player.game = game
    player.save(update_fields=['game'])
    alert_game_lobby_player_joined(game, player)
    if game.is_public:
        if game.is_full:
            update_lobby_list_remove_game(game)
        else:
            update_lobby_list_player_count(game, game.players.count())


@transaction.atomic
def player_leave_lobby(player):
    game = player.game
    if game.is_started:
        raise TypeError("game is already started")
    game_was_full = game.is_full
    player_was_lobby_leader = player.is_lobby_owner
    player.game = None
    player.is_lobby_owner = False
    player.save(update_fields=['game', 'is_lobby_owner'])
    if not game.players.exclude(id=player.id).exists():
        # This lobby is now empty
        update_lobby_list_remove_game(game)
        game.delete()

    else:
        # Still players in this lobby
        push_player_quit_game_event(game, player)
        if game_was_full:
            if game.game_type == Game.GAME_TYPE_CHOICE_CONNECT_QUAT:
                update_lobby_list_add_connect_quatro(game, game.board)
            else:
                raise NotImplementedError()
        else:
            update_lobby_list_player_count(game, game.players.count())
        
        if player_was_lobby_leader:
            new_leader = sorted(game.players.all(), key=lambda p: random.random())[0]
            new_leader.is_lobby_owner = True
            new_leader.save(update_fields=['is_lobby_owner'])
            push_player_promoted_to_lobby_leader(new_leader, game)


# async channel layer functions

@async_to_sync
async def alert_game_lobby_player_joined(game, player):
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        game.channel_layer_name,
        {
            "type":"player.joined",
            "playerSlug":player.slug,
            "playerHandle":player.handle,
        }
    )

@async_to_sync
async def push_player_quit_game_event(game, player):
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        game.channel_layer_name,
        {
            "type":"player.quit",
            "playerSlug":player.slug,
        }
    )

@async_to_sync
async def push_player_promoted_to_lobby_leader(player, game):
    print("push_player_promoted_to_lobby_leader()")
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        game.channel_layer_name,
        {
            "type":"player.promoted",
            "playerSlug":player.slug,
        }
    )

@async_to_sync
async def update_lobby_list_player_count(game, new_count):
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        LobbyRoomsConsumer.ROOM_NAME_DEFAULT,
        {
            "type":"room.player.count.update",
            "slug":game.slug,
            "count":new_count,
        }
    )

@async_to_sync
async def update_lobby_list_remove_game(game):
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        LobbyRoomsConsumer.ROOM_NAME_DEFAULT,
        {
            "type":"room.remove",
            "slug":game.slug,
        }
    )

@async_to_sync
async def update_lobby_list_add_connect_quatro(game, board):
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        LobbyRoomsConsumer.ROOM_NAME_DEFAULT,
        {
            "type":"room.add",
            "name":game.name,
            "slug":game.slug,
            "player_count":1,
            "max_players":game.max_players,
            "connect_quatro_board":{
                'board_length_x':board.board_length_x,
                'board_length_y':board.board_length_y,
            }
        }
    )
