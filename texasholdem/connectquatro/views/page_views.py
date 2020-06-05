
""" Connect Quatro Page Views
"""
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import Http404
from lobby.models import Game


@login_required
def game_page(request, slug):
    user = request.user
    player = user.player

    game = get_object_or_404(
        Game, slug=slug, game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT)
    board = game.board
    players = game.players.order_by('turn_order')
    
    if player.game != game:
        return redirect("page-lobby-login-redirect")
    
    if not game.is_started:
        return redirect("page-lobby-login-redirect")
    
    rows_count =  board.board_length_y
    cols_count = board.board_length_x

    data = {
        'chat_socket_url':'/game/chat/',
        'game':game,
        'board':board,
        'player':player,
        'players':players,
        'archived_players': game.archived_players.order_by("turn_order"),
        'rows_list':range(rows_count),
        'cols_list':range(cols_count),
    }
    return render(request, "game_page.html", data)
