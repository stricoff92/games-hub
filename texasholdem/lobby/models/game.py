
from collections import Counter
from django.db import models

from .utils import generate_slug
from lobby.models import Player

class GameManager(models.Manager):
    def get_publically_joinable_games(self):
        games = super().get_queryset().filter(
            is_public=True, is_started=False)
        players_counts = Counter(Player.objects.filter(
            game__in=games).values_list("game_id", flat=True))
        
        not_full_game_ids = []
        for game in games.values('id', 'max_players'):
            if players_counts[game['id']] < game['max_players']:
                not_full_game_ids.append(game['id'])
        
        return games.filter(id__in=not_full_game_ids)
            

class Game(models.Model):

    objects = GameManager()

    slug = models.SlugField(unique=True)   
    name = models.CharField(max_length=24)

    GAME_TYPE_CHOICE_TEXAS_HOLDEM = 'texasholdem'
    GAME_TYPE_CHOICE_CONNECT_QUAT = 'connectquat'
    GAME_TYPE_CHOICES = (
        (GAME_TYPE_CHOICE_CONNECT_QUAT, "Connect-Quat",),
        (GAME_TYPE_CHOICE_TEXAS_HOLDEM, "Texas Hold'Em",),
    )
    game_type = models.CharField(max_length=24, choices=GAME_TYPE_CHOICES)
    max_players = models.IntegerField(default=2)

    is_public = models.BooleanField(default=True)
    is_started = models.BooleanField(default=False)
    is_over = models.BooleanField(default=False)

    archived_players = models.ManyToManyField(
        'lobby.Player', related_name="archived_games")

    @property
    def is_pregame(self):
        return not self.is_started and not self.is_over and self.players.exists()

    @property
    def is_full(self):
        return self.players.count() >= self.max_players

    @property
    def channel_layer_name(self):
        return f"{self.slug}"
    
    @property
    def chat_channel_layer_name(self):
        return f"{self.slug}-chat"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_slug(Game)
        return super().save(*args, **kwargs)
    
    def __str__(self):
        return f"<Game {self.id} {self.game_type} {self.name}>"
