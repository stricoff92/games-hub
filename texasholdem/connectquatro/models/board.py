

from django.db import models


class Board(models.Model):

    STATE_KEY_NEXT_PLAYER_TO_ACT = "next_to_act"
    STATE_KEY_BOARD_LIST = "board_list"

    game = models.OneToOneField('lobby.Game', on_delete=models.CASCADE)
    board_state = models.CharField(max_length=1000)

    max_to_win = models.IntegerField(default=4)

    board_length_x = models.IntegerField(default=7)
    board_length_y = models.IntegerField(default=7)

