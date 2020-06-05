
from django.conf import settings
from django.db import models

from .utils import generate_slug


class Player(models.Model):

    slug = models.SlugField(unique=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    handle = models.CharField(max_length=12)

    game = models.ForeignKey('lobby.Game', on_delete=models.SET_NULL, related_name="players", blank=True, null=True)
    is_lobby_owner = models.BooleanField(default=False)
    is_ready = models.BooleanField(default=False)

    turn_order = models.IntegerField(blank=True, null=True, default=None)

    LOBBY_STATUS_JOINED = 'joined'
    LOBBY_STATUS_READY = 'ready'
    LOBBY_STATUS_CHOICES = (
        (LOBBY_STATUS_JOINED, 'Joined'),
        (LOBBY_STATUS_READY, 'Ready'),
    )

    lobby_status = models.CharField(
        max_length=12, choices=LOBBY_STATUS_CHOICES,
        default=LOBBY_STATUS_JOINED)

    COLOR_CHOICES = (
        ('#a80000', 'Red'),
        ('#c78500', 'Orange'),
        ('#918d00', 'Yellow'),
        ('#00803c', 'Green'),
        ('#0039bf', 'Blue'),
        ('#6b4b9c', 'Purple'),
        ('#787878', 'Gray'),
        ('#5c4300', 'Brown'),
    )
    color = models.CharField(
        max_length=8, choices=COLOR_CHOICES, blank=True, null=True, default=None)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_slug(Player)
        return super().save(*args, **kwargs)

    def __str__(self):
        return str(self.user)
