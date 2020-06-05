

import random
from uuid import uuid4

from django.db import transaction
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from lobby.models.game import Game
from lobby.models.player import Player
from connectquatro.models import Board


def _true_or_false(probability_true=0.5):
    x = random.randint(1, 100)
    return (probability_true * 100) > x


class Command(BaseCommand):

    help = ''

    @transaction.atomic
    def handle(self, *args, **options):
        games_to_add = 25
        batch = '2f82ea29'
        users = list(User.objects.filter(
            username__contains=batch, player__game__isnull=True))

        for i in range(games_to_add):
            number_of_players = random.randint(2,4)
            game = Game.objects.create(
                name="a game room",
                game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT,
                max_players=number_of_players)
            
            print("game created", game)
        
            cq_board = Board(game=game)
            if number_of_players > 2 and _true_or_false():
                cq_board.board_length_x = random.randint(9,15)
                cq_board.board_length_y = random.randint(9,15)
                cq_board.max_to_win = random.randint(4, 6)
            else:
                cq_board.board_length_x = 7
                cq_board.board_length_y = 7
            cq_board.save()
            print("board created", cq_board)

            player_owner = users.pop(random.randint(0, len(users) - 1)).player
            player_owner.is_lobby_owner = True
            player_owner.game = game
            player_owner.save()
            print("attaching player as owner", player_owner )

            if number_of_players > 2 and _true_or_false(probability_true=0.6):
                # Add another player to the room
                player_to_add = users.pop(random.randint(0, len(users) - 1)).player
                player_to_add.game = game
                player_to_add.save()
                print('attaching player as joiner', player_to_add)


