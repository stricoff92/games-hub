
from django.db import models

from lobby.models.base import AbstractBaseModel
from .utils import generate_slug

class GameFeedMessage(AbstractBaseModel):

    game = models.ForeignKey("lobby.Game", on_delete=models.CASCADE)

    message = models.CharField(max_length=300)

    # Connect Quatro message types
    MESSAGE_TYPE_PLAYER_MOVE_DROP_CHIP = 'move-dc'

    # Poker message types
    MESSAGE_TYPE_PLAYER_CHECK = 'move-check'
    MESSAGE_TYPE_PLAYER_CALLS = 'move-call'
    MESSAGE_TYPE_PLAYER_RAISE = 'move-raise'
    MESSAGE_TYPE_PLAYER_FOLD = 'move-fold'

    # All games message types
    MESSAGE_TYPE_PLAYER_QUIT = 'quit'
    MESSAGE_TYPE_GAME_STATUS = 'status'

    MESSAGE_TYPE_CHOICES = (
        (MESSAGE_TYPE_PLAYER_MOVE_DROP_CHIP, "Player Dropped A Chip",),
        (MESSAGE_TYPE_PLAYER_CHECK, "Player Checks",),
        (MESSAGE_TYPE_PLAYER_CALLS, "Player Calls",),
        (MESSAGE_TYPE_PLAYER_RAISE, "Player Raises",),
        (MESSAGE_TYPE_PLAYER_FOLD, "Player Folds",),
        (MESSAGE_TYPE_PLAYER_QUIT, "Player Quit",),
        (MESSAGE_TYPE_GAME_STATUS, "Game Status",),
    )
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES)

    MESSAGE_TYPE_TO_FAS_CLASSES = {
        MESSAGE_TYPE_PLAYER_MOVE_DROP_CHIP: "fas fa-arrow-alt-circle-down",
        MESSAGE_TYPE_PLAYER_CHECK: "fas fa-check-circle",
        MESSAGE_TYPE_PLAYER_CALLS: "fas fa-balance-scale",
        MESSAGE_TYPE_PLAYER_RAISE: "fas fa-chart-line",
        MESSAGE_TYPE_PLAYER_FOLD: "fas fa-times-circle",
        MESSAGE_TYPE_PLAYER_QUIT: "fas fa-hand-peace",
        MESSAGE_TYPE_GAME_STATUS: "fas fa-bell",
    }

    @property
    def font_awesome_classes(self):
        return self.MESSAGE_TYPE_TO_FAS_CLASSES[self.message_type]
