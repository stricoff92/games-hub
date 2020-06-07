
import json
import random

from asgiref.sync import async_to_sync
from django.db import transaction
from channels.layers import get_channel_layer

from connectquatro.models import Board
from connectquatro import tasks as cq_tasks
from lobby.models import Player, Game, CompletedGame, GameFeedMessage
from lobby import lib as lobby_lib


class ColumnIsFullError(Exception):
    pass

class ColumnOutOfRangeError(Exception):
    pass

class SerializedDataMismatchedError(Exception):
    pass


# sync database functions

def board_state_to_obj(board:Board) -> str:
    return json.loads(board.board_state)

def board_obj_to_serialized_state(board:dict) -> str:
    return json.dumps(board)

def get_active_player_id_from_board(board:Board):
    board_state = board_state_to_obj(board)
    return board_state[Board.STATE_KEY_NEXT_PLAYER_TO_ACT]


def get_next_player_turn(board:Board):
    game_data = board_state_to_obj(board)
    return game_data[Board.STATE_KEY_NEXT_PLAYER_TO_ACT]


def get_game_over_state(board:Board) -> tuple:
    if board.game.is_over:
        winning_player =  board.game.completedgame.winners.first()
        return True, winning_player

    winner = get_winning_player(board)
    if winner:
        return True, winner
    game = board.game
    if game.players.count() == 1:
        return True, game.players.first()

    return False, None

def get_winning_player(board:Board) -> Player:
    board.refresh_from_db()
    game_data = board_state_to_obj(board)
    board_list = game_data[Board.STATE_KEY_BOARD_LIST]

    for player in board.game.archived_players.all():
        

        # Check for horizontal N in a rows
        for row_ix, row in enumerate(board_list):
            in_a_row = 0
            for col_ix, player_in_slot in enumerate(row):
                if player_in_slot == player.id:
                    in_a_row += 1
                else:
                    in_a_row = 0
                if in_a_row == board.max_to_win:
                    return player

        # Check for verticle N in a rows
        for col_ix in range(len(board_list[0])):
            column = [board_list[row_ix][col_ix] for row_ix in range(len(board_list))]
            in_a_row = 0
            for row_ix, player_in_slot in enumerate(column):
                if player_in_slot == player.id:
                    in_a_row += 1
                else:
                    in_a_row = 0
                if in_a_row == board.max_to_win:
                    return player
        
        # check for diagonal N in a row
        number_of_rows = len(board_list)
        for row_ix, row in enumerate(board_list):
            for col_ix, player_in_slot in enumerate(row):
                if player_in_slot != player.id:
                    continue
                
                # check for diagonal down right
                if (
                    col_ix <= (len(row) - board.max_to_win)             # we have space to the right
                    and row_ix <= (number_of_rows - board.max_to_win)): # we have space below

                    in_a_row = 1
                    for offset in range(1, board.max_to_win):
                        row_ix_to_check = row_ix + offset
                        col_ix_to_check = col_ix + offset
                        next_chip = board_list[row_ix_to_check][col_ix_to_check]
                        if next_chip == player.id:
                            in_a_row += 1

                    if in_a_row >= board.max_to_win:
                        return player

                # check for diagonal down left
                if (
                    col_ix >= (len(row) - board.max_to_win)             # we have space to the left
                    and row_ix <= (number_of_rows - board.max_to_win)): # we have space below

                    in_a_row = 1
                    for offset in range(1, board.max_to_win):
                        row_ix_to_check = row_ix + offset
                        col_ix_to_check = col_ix - offset
                        next_chip = board_list[row_ix_to_check][col_ix_to_check]
                        if next_chip == player.id:
                            in_a_row += 1

                    if in_a_row >= board.max_to_win:
                        return player


def cycle_player_turn(board:Board) -> tuple:
    board_state = board_state_to_obj(board)
    current_player_id = board_state[Board.STATE_KEY_NEXT_PLAYER_TO_ACT]
    player_ids = list(board.game.players.order_by('turn_order').values_list('id', flat=True))

    current_player_position = player_ids.index(current_player_id)
    restart_order = current_player_position == len(player_ids) - 1
    if restart_order:
        new_player_to_act = player_ids[0]
    else:
        new_player_to_act = player_ids[current_player_position + 1]
    
    board_state[Board.STATE_KEY_NEXT_PLAYER_TO_ACT] = new_player_to_act
    board.board_state = board_obj_to_serialized_state(board_state)
    board.save(update_fields=['board_state'])
    return board, new_player_to_act



@transaction.atomic
def drop_chip(board:Board, player:Player, column_ix:int):
    game_data = board_state_to_obj(board)
    board_list = game_data[Board.STATE_KEY_BOARD_LIST]
    try:
        target_colum = [row[column_ix] for row in board_list]
    except IndexError:
        raise ColumnOutOfRangeError()

    if target_colum[0]:
        raise ColumnIsFullError()
    
    next_row_ix = None
    for last_ix, chip in enumerate(target_colum):
        if chip:
            next_row_ix = last_ix - 1
            break

    # This column is empty
    if next_row_ix is None:
        next_row_ix = len(target_colum) - 1

    
    board_list[next_row_ix][column_ix] = player.id
    game_data[Board.STATE_KEY_BOARD_LIST] = board_list
    board.board_state = board_obj_to_serialized_state(game_data)
    board.save(update_fields=['board_state'])
    return board

@transaction.atomic
def start_game(game):
    # Set game flags.
    game.is_started = True
    game.save(update_fields=['is_started'])
    game.archived_players.set(game.players.all())

    # Set player turn order and color.
    colors = [c[0] for c in Player.COLOR_CHOICES]
    colors.sort(key=lambda c: random.random())
    player_ids = game.players.values_list("id", flat=True)
    random_order_player_ids = sorted(
        player_ids, key=lambda v: random.random())
    for ix, player_id in enumerate(random_order_player_ids):
        turn_order = ix + 1
        player_color = colors.pop(0)
        Player.objects.filter(id=player_id).update(
            turn_order=turn_order,
            color=player_color,
            lobby_status=Player.LOBBY_STATUS_JOINED)

    # Set board state
    board = Board.objects.get(game=game)
    board_state = {
        Board.STATE_KEY_NEXT_PLAYER_TO_ACT:random_order_player_ids[0],
        Board.STATE_KEY_BOARD_LIST:[
            [None for i in range(board.board_length_x)]
                for j in range(board.board_length_y)
        ]
    }
    board.board_state = board_obj_to_serialized_state(board_state)
    board.save(update_fields=['board_state'])

    # Fire off websocket events
    alert_game_lobby_game_started(game) # TODO: clean code move to diff abstraction
    lobby_lib.update_lobby_list_remove_game(game)


def get_game_state(board, requesting_player=None) -> tuple:
    game = board.game
    board_state = board_state_to_obj(board)
    board_list = board_state[Board.STATE_KEY_BOARD_LIST]
    data = {
        'board_list':board_list,
        'players':[],
        'winner':None,
        'game_over':False,
        'active_player':None,
        'next_player_slug':None,
    }

    game_over, winning_player = get_game_over_state(board)
    if game_over:
        data['game_over'] = True
        data['winner'] = {
            'handle':winning_player.handle,
            'slug':winning_player.slug,
        }
    
    if not winning_player:
        players = game.players.all()
        next_player_id_to_act = board_state[Board.STATE_KEY_NEXT_PLAYER_TO_ACT]
        player_to_move = players.filter(id=next_player_id_to_act).first()
        data['next_player_slug'] = player_to_move.slug

        if requesting_player:
            data['active_player'] = player_to_move == requesting_player
    
    data['players'] = [p for p in board.game.players.values('slug', 'id', 'color')]
    game_over = winning_player is not None

    return data, game_over # TUPLE !


@transaction.atomic
def remove_player_from_active_game(player):
    game = player.game
    if not game.is_started:
        raise TypeError("game is not started")
    if game.is_over:
        raise TypeError("game already over")

    player.game = None
    player.is_lobby_owner = False
    player.save(update_fields=['game', 'is_lobby_owner'])

    game_over_gfm = None
    gfm = GameFeedMessage.objects.create(
        game=game, message_type=GameFeedMessage.MESSAGE_TYPE_PLAYER_QUIT,
        message=f"{player.handle} quit")

    board = game.board
    board_state = board_state_to_obj(board)
    players_left = game.players.all()
    players_left_count = players_left.count()

    if players_left_count > 1:
        # Still players left. The game continues.
        current_player_turn_id = board_state[Board.STATE_KEY_NEXT_PLAYER_TO_ACT]
        if current_player_turn_id == player.id:
            # Adjust active player turn. Active player just left.
            next_turn_player_id = players_left.order_by('turn_order').first().id

            board_state[Board.STATE_KEY_NEXT_PLAYER_TO_ACT] = next_turn_player_id
            board.board_state = board_obj_to_serialized_state(board_state)
            board.save(update_fields=['board_state'])
            game.tick_count = game.tick_count + 1
            game.save(update_fields=['tick_count'])
            cq_tasks.cycle_player_turn_if_inactive.delay(
                game.id, next_turn_player_id, game.tick_count)
    
    elif players_left_count == 1:
        # 1x player left. End the game
        game.is_over = True
        game.save()
        cg = CompletedGame.objects.create(game=game)
        last_player = game.players.first()
        cg.winners.set([last_player])

        game_over_gfm = GameFeedMessage.objects.create(
            game=game, message_type=GameFeedMessage.MESSAGE_TYPE_GAME_STATUS,
            message=f"{last_player.handle} wins")

    
    game_state, is_over = get_game_state(board)
    alert_game_players_to_new_move(game, game_state)
    push_new_game_feed_message(gfm)
    if game_over_gfm:
        push_new_game_feed_message(game_over_gfm)


@transaction.atomic
def remove_player_from_completed_game(player):
    game = player.game
    if not game.is_over:
        raise TypeError("game is not over")
    
    player.game = None
    player.is_lobby_owner = False
    player.save(update_fields=['game', 'is_lobby_owner'])

# async channel layer functions

@async_to_sync
async def alert_game_lobby_game_started(game):
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        game.channel_layer_name, {"type":"game.started"})

@async_to_sync
async def alert_game_players_to_new_move(game, game_state):
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        game.channel_layer_name, 
        {
            "type":"game.move",
            "game_state":game_state,
        })

@async_to_sync
async def update_count_down_clock(game, player_slug, seconds_left):
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        game.channel_layer_name, 
        {
            "type":"countdown.update",
            "player_slug":player_slug,
            "seconds":seconds_left,
        })

@async_to_sync
async def push_new_game_feed_message(game_feed_message:GameFeedMessage):
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        game_feed_message.game.channel_layer_name, 
        {
            "type": "new.game.feed.message",
            "message": game_feed_message.message,
            "message_type": game_feed_message.message_type,
            "font_awesome_classes": game_feed_message.font_awesome_classes,
            "created_at":game_feed_message.created_at.isoformat(),
        })
