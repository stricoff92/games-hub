""" CELERY Background tasks.
"""

import time

from django.db import transaction

from connectquatro import lib as cq_lib
from connectquatro.models import Board
from lobby.models import Game, Player
from texasholdem.celery_conf import app


@app.task
def cycle_player_turn_if_inactive(game_id:int, active_player_id:int, original_tick_count:int):
    """ This task is started when a players turn starts.
        After the delay, check if it's still this players turn. If so end
        their turn and cycle to the next player
    """
    game = Game.objects.get(id=game_id)
    player = Player.objects.get(id=active_player_id)

    max_seconds_per_turn = game.max_seconds_per_turn
    for elapsed_time in range(0, max_seconds_per_turn, 3):
        game.refresh_from_db()
        if game.tick_count > original_tick_count:
            return
        seconds_remaining = max_seconds_per_turn - elapsed_time
        cq_lib.update_count_down_clock(game, player.slug, seconds_remaining)
        time.sleep(3)
    
    game.refresh_from_db()
    if game.tick_count > original_tick_count:
        return
    
    # Player has yet to move. End their turn
    board = game.board
    with transaction.atomic():
        board, next_player_id_turn = cq_lib.cycle_player_turn(board)
        game_state, _ = cq_lib.get_game_state(board)
        cq_lib.alert_game_players_to_new_move(game, game_state)

        # Increment tick counter
        new_tick_count = original_tick_count + 1
        game.tick_count = new_tick_count
        game.save(update_fields=['tick_count'])

    # Restart task for next player
    cycle_player_turn_if_inactive.delay(game_id, next_player_id_turn, new_tick_count)
