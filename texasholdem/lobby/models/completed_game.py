
from django.db import models

from .utils import generate_slug
from lobby.models import Game


        
class CompletedGame(models.Model):
    game = models.OneToOneField(Game, on_delete=models.SET_NULL, null=True)

    WINNER_TYPE_DRAW = "<< DRAW >>"
    winners = models.ManyToManyField("lobby.Player")

    def winners_list(self):
        if self.winners == self.WINNER_TYPE_DRAW:
            return []
        return winners.replace(" ", "").split(",")
