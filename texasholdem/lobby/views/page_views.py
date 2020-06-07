
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from rest_framework import status

from lobby.forms import LoginForm, RegistrationForm
from lobby.models import Game
from lobby.utils import random_room_name


@login_required
def rooms_page(request):
    """ Serve up the lobby list HTML template.
    """

    user = request.user
    player = user.player
    if player.game:
        return redirect("page-lobby-login-redirect")
    
    ex_room_name = random_room_name()
    data = {
        'game_types':Game.GAME_TYPE_CHOICES,
        'chat_socket_url':'/lobby/chat/',
        'example_name':ex_room_name.title(),
    }
    return render(request, 'lobby_list.html', data)

@login_required
def game_lobby_page(request, slug):
    user = request.user
    player = user.player

    game = get_object_or_404(
        Game, slug=slug, game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT)
    
    if player.game != game:
        return redirect("page-lobby-login-redirect")

    if game.is_started:
        return redirect("page-lobby-login-redirect")

    if game.game_type == Game.GAME_TYPE_CHOICE_CONNECT_QUAT:
        board = game.board
        data = {
            'chat_socket_url':'/game/chat/',
            'game_socket_url':'/connectquatro/',
            'game':game,
            'player':player,
            'rules' :[
                f'Max players: { game.max_players }',
                f'Chips to win: { board.max_to_win }',
                f'Board size: { board.board_length_x } x { board.board_length_y }',
                f'Seconds per turn: { game.max_seconds_per_turn }',
            ]
        }
        return render(request, "game_lobby.html", data)

@login_required
def lobby_join_with_join_game_id(request, join_game_id):
    user = request.user
    player = user.player
    if player.game:
        return redirect('page-lobby-login-redirect')

    game = get_object_or_404(
        Game, join_game_id=join_game_id, is_started=False, is_over=False)
    
    return render(request, "join_game_by_id.html", {'game':game})


def login_page(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()

        user = authenticate(
            request, 
            username=form.cleaned_data['username'], 
            password=form.cleaned_data['password'])
        if user is not None:
            login(request, user)
            return redirect('page-lobby-login-redirect')
        else:
            data = {
                "error":"invalid username/password",
                "username":form.cleaned_data['username'],
                'form':LoginForm(),
            }
            return render(
                request, 'login.html', data,
                status=status.HTTP_403_FORBIDDEN) 
    
    elif request.method == 'GET':
        if request.user.is_authenticated:
            return redirect('page-lobby-login-redirect')
        return render(request, 'login.html', {'form':LoginForm()})
    
    else:
        return HttpResponse(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)

@login_required
def login_redirect(request):
    user = request.user
    player = user.player
    game = player.game
    if not game:
        return redirect('page-lobby-list')
    
    elif game.game_type == Game.GAME_TYPE_CHOICE_CONNECT_QUAT:
        if game.is_started:
            return redirect("page-connectquat", slug=game.slug)
        else:
            return redirect("page-game-lobby", slug=game.slug)

    else:
        raise NotImplementedError()

def logout_page(request):
    logout(request)
    return redirect('page-lobby-login')

def register(request):
    form = RegistrationForm(request.POST)


