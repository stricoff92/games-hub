
from collections import Counter

from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib.auth.decorators import login_required

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from lobby.models import Game, Player
from lobby.forms import (
    NewConnectQuatroRoomForm,
    GameTypeSelectionForm,
    GamePrivacySettingsForm,
    GameJoinIdForm,
)
from lobby import lib as lobby_lib
from connectquatro import lib as cq_lib
from connectquatro.models import Board as CQboard
from connectquatro import tasks as cq_tasks


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_lobby(request):
    user = request.user
    player = user.player

    if player.game:
        return Response(
            "player already in game",
            status.HTTP_400_BAD_REQUEST)
    
    game_type_form = GameTypeSelectionForm(request.data)
    if not game_type_form.is_valid():
        return Response(form.errors, status.HTTP_400_BAD_REQUEST) 
    game_type = game_type_form.cleaned_data['roomtype']

    game_privacy_form = GamePrivacySettingsForm(request.data)
    if not game_privacy_form.is_valid():
        return Response(form.errors, status.HTTP_400_BAD_REQUEST) 
    
    privacy = game_privacy_form.cleaned_data['privacy']
    is_public = privacy == 'public'

    if game_type == Game.GAME_TYPE_CHOICE_CONNECT_QUAT:
        cq_form = NewConnectQuatroRoomForm(request.data)
        if not cq_form.is_valid():
            return Response(cq_form.errors, status.HTTP_400_BAD_REQUEST)
        game_name = cq_form.cleaned_data['roomname']
        board_length_x = cq_form.cleaned_data['boarddimx']
        board_length_y = cq_form.cleaned_data['boarddimy']
        max_players = cq_form.cleaned_data['boardplayercount']
        max_to_win = cq_form.cleaned_data['boardwincount']
        max_seconds_per_turn = cq_form.cleaned_data['max_seconds_per_turn']

        game = lobby_lib.player_create_connectquat_lobby(
            player, game_name, board_length_x, board_length_y, max_players, max_to_win,
            max_seconds_per_turn, is_public=is_public)
        data = {
            'id':game.id,
            'slug':game.slug,
        }
        return Response(data, status.HTTP_201_CREATED)
    else:
        raise NotImplementedError()

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_game(request):
    user = request.user
    player = user.player
    game = player.game

    if not game:
        return Response(
            "Player not part of a lobby", status.HTTP_400_BAD_REQUEST)
    if not player.is_lobby_owner:
        return Response(
            "Player not lobby owner", status.HTTP_400_BAD_REQUEST)
    if game.is_started:
        return Response(
            "Game is already started", status.HTTP_400_BAD_REQUEST)
    if game.players.count() < 2:
        return Response(
            "Game needs at least 2 players to start", status.HTTP_400_BAD_REQUEST)

    if game.game_type == Game.GAME_TYPE_CHOICE_CONNECT_QUAT:
        cq_lib.start_game(game)
        active_player_id = cq_lib.get_active_player_id_from_board(game.board)
        cq_tasks.cycle_player_turn_if_inactive.delay(
            game.id, active_player_id, game.tick_count)
    else:
        raise NotImplementedError()
    
    return Response({}, status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initialize_game_start_downdown(request):
    user = request.user
    player = user.player
    game = player.game

    if not game:
        return Response(
            "Player not part of a lobby", status.HTTP_400_BAD_REQUEST)
    if not player.is_lobby_owner:
        return Response(
            "Player not lobby owner", status.HTTP_400_BAD_REQUEST)
    if game.is_started:
        return Response(
            "Game is already started", status.HTTP_400_BAD_REQUEST)
    if game.players.count() < 2:
        return Response(
            "Game needs at least 2 players to start", status.HTTP_400_BAD_REQUEST)

    if game.game_type == Game.GAME_TYPE_CHOICE_CONNECT_QUAT:
        cq_lib.start_game(game)
    else:
        raise NotImplementedError()
    
    return Response({}, status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_lobby(request, slug):
    user = request.user
    player = user.player

    if player.game:
        return Response(
            "You are already in game",
            status.HTTP_400_BAD_REQUEST)
    
    game = get_object_or_404(Game, slug=slug)
    if game.is_started:
        return Response(
            "Lobby is no longer joinable", status.HTTP_400_BAD_REQUEST)  
    if game.is_full:
        return Response(
            "Lobby is full", status.HTTP_400_BAD_REQUEST)

    if game.is_over:
        return Response(
            "game is over", status.HTTP_400_BAD_REQUEST)
    
    if not game.is_public:
        join_id_form = GameJoinIdForm(request.data)
        if not join_id_form.is_valid():
            return Response(join_id_form.errors, status.HTTP_400_BAD_REQUEST)

        join_game_id = join_id_form.cleaned_data["join_game_id"]
        if join_game_id != game.join_game_id:
            return Response(
                "invalid join_game_id", status.HTTP_400_BAD_REQUEST)



    lobby_lib.player_join_lobby(player, game)
    return Response({}, status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def leave_lobby(request):
    user = request.user
    player = user.player
    if not player.game:
        return Response(
            "player not in a game", status.HTTP_400_BAD_REQUEST) 
    
    if not player.game.is_started:
        lobby_lib.player_leave_lobby(player)

    elif not player.game.is_over:
        if player.game.game_type == Game.GAME_TYPE_CHOICE_CONNECT_QUAT:
            cq_lib.remove_player_from_active_game(player)

    else:
        if player.game.game_type == Game.GAME_TYPE_CHOICE_CONNECT_QUAT:
            cq_lib.remove_player_from_completed_game(player)

    return Response({}, status.HTTP_200_OK)


@api_view(['get'])
@permission_classes([IsAuthenticated])
def see_lobbies(request):
    user = request.user
    player = user.player

    if player.game:
        return Response("You are already in game", status.HTTP_400_BAD_REQUEST)
    
    games = Game.objects.get_publically_joinable_games()
    games = games.order_by("-pk")

    players = Counter(Player.objects
        .filter(game__in=games)
        .values_list("game_id", flat=True))

    cq_boards = (CQboard.objects
        .filter(game__in=games)
        .values('game_id', 'board_length_x', 'board_length_y',))
    cq_boards = {b['game_id']:b for b in cq_boards}

    games = games.values("id", "name", "slug", "game_type", "max_players",)
    rows = []
    for ix, game in enumerate(games):
        game_id = game['id']
        if game['game_type'] == Game.GAME_TYPE_CHOICE_CONNECT_QUAT:
            games[ix]['connect_quatro_board'] = cq_boards.get(game_id)
            games[ix]['player_count'] = players[game_id]

    return Response(games)
