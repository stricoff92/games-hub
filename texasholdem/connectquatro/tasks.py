""" CELERY Background tasks.
"""

import time

from connectquatro import lib as cq_lib
from connectquatro.models import Board
from lobby.models import Game
from texasholdem.celery_conf import app


@app.task
def cycle_player_turn_if_inactive(game_id:int, original_tick_count:int):
    """ This task is started when a players turn starts.
        After the delay, check if it's still this players turn. If so end
        their turn and cycle to the next player
    """
    game = Game.objects.get(id=game_id)
    time.sleep(game.max_seconds_per_turn)
    
    game.refresh_from_db()
    if game.tick_count > original_tick_count:
        return
    
    # Player has yet to move. End their turn
    board = game.board
    board, next_player_turn = cq_lib.cycle_player_turn(board)
    game_state, _ = cq_lib.get_game_state(board)
    cq_lib.alert_game_players_to_new_move(game, game_state)

    # Increment tick counter
    new_tick_count = original_tick_count + 1
    game.tick_count = new_tick_count
    game.save(update_fields=['tick_count'])

    # Restart task for next player
    cycle_player_turn_if_inactive.delay(game_id, new_tick_count)
