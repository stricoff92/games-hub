

from functools import wraps

from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from lobby.models import Game, CompletedGame
from connectquatro import lib as cq_lib
from connectquatro.forms import ConnectQuatroMoveForm
from connectquatro.models import Board
from django.db import transaction
from texasholdem.utils import get_user_player_game


def is_playing_active_connect_quatro_game(function):
    @wraps(function)
    def decorated_function(request, *args, **kwargs):
        try:
            game = get_user_player_game(request)[2]
        except AttributeError as e:
            print(e)
            return  Response("game not found", status.HTTP_404_NOT_FOUND)
        
        if game.game_type != Game.GAME_TYPE_CHOICE_CONNECT_QUAT or not game.is_started:
            return Response("invalid game state", status.HTTP_400_BAD_REQUEST)

        return function(request, *args, **kwargs)
        

    
    return decorated_function

def is_active_player_in_connect_quatro(function):
    @wraps(function)
    def decorated_function(request, *args, **kwargs):
        try:
            player, game = get_user_player_game(request)[1:]
        except AttributeError as e:
            print(e)
            return  Response("game not found", status.HTTP_404_NOT_FOUND)
        
        if not game:
            return  Response("game not found", status.HTTP_404_NOT_FOUND)
        
        if game.game_type != Game.GAME_TYPE_CHOICE_CONNECT_QUAT or not game.is_started:
            return Response("invalid game state", status.HTTP_400_BAD_REQUEST)
        
        if game.is_over:
            return Response("game over", status.HTTP_400_BAD_REQUEST)
        
        board_state = cq_lib.board_state_to_obj(game.board)
        next_player_id = board_state[Board.STATE_KEY_NEXT_PLAYER_TO_ACT]
        if next_player_id != player.id:
            return Response("turn order error", status.HTTP_400_BAD_REQUEST)
        
        return function(request, *args, **kwargs)
        

    return decorated_function


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@is_active_player_in_connect_quatro
def make_move(request):
    user, player, game = get_user_player_game(request)
    board = game.board
    form = ConnectQuatroMoveForm(
        request.data, max_column_index=board.board_length_x - 1)
    if not form.is_valid():
        return Response(form.errors, status.HTTP_400_BAD_REQUEST)
    
    user, player, game = get_user_player_game(request)

    with transaction.atomic():
        try:
            board = cq_lib.drop_chip(
                board, player, form.cleaned_data['column_index'])
        except (cq_lib.ColumnIsFullError,
                cq_lib.ColumnOutOfRangeError):
            return Response(
                "illegal move", status.HTTP_400_BAD_REQUEST)
        board, new_player_to_act = cq_lib.cycle_player_turn(board)
        
        game_over, winning_player = cq_lib.get_game_over_state(board)
        if game_over:
            game.is_over = True
            game.save(update_fields=['is_over'])
            cq = CompletedGame.objects.create(game=game)
            cq.winners.set([winning_player])
    
    game_state, _ = cq_lib.get_game_state(board, player)

    game_state, game_over = cq_lib.get_game_state(board, player)
    cq_lib.alert_game_players_to_new_move(game, game_state)
    game_state['active_player'] = False
    if game_state['winner']:
        game_state['player_won'] = game_state['winner']['slug'] == player.slug
    return Response(game_state, status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@is_playing_active_connect_quatro_game
def ping(request):
    user, player, game = get_user_player_game(request)
    data, _ = cq_lib.get_game_state(
        game.board, requesting_player=player)
    if data['winner']:
        data['player_won'] = data['winner']['slug'] == player.slug
    return Response(data, status.HTTP_200_OK)
