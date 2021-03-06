""" CELERY Background tasks.
"""

import time

from django.db import transaction

from connectquatro import lib as cq_lib
from connectquatro.models import Board
from lobby.models import Game, Player, GameFeedMessage
from texasholdem.celery_conf import app
from texasholdem.environment import is_testing


@app.task
def cycle_player_turn_if_inactive(game_id:int, active_player_id:int, original_tick_count:int):
    """ This task is started when a players turn starts.
        After the delay, check if it's still this players turn. If so end
        their turn and cycle to the next player
    """
    is_testing_env = is_testing()
    game = Game.objects.get(id=game_id)
    player = Player.objects.get(id=active_player_id)

    max_seconds_per_turn = game.max_seconds_per_turn
    for elapsed_time in range(0, max_seconds_per_turn, 3):
        game.refresh_from_db()
        if game.tick_count > original_tick_count or game.is_over:
            return
        seconds_remaining = max_seconds_per_turn - elapsed_time
        cq_lib.update_count_down_clock(game, player.slug, seconds_remaining)
        if not is_testing_env:
            time.sleep(3)
    
    game.refresh_from_db()
    if game.tick_count > original_tick_count:
        return
    
    # Player has yet to move. End their turn
    board = game.board
    with transaction.atomic():
        board, next_player_id_turn = cq_lib.cycle_player_turn(board)

        # Increment tick counter
        new_tick_count = original_tick_count + 1
        game.tick_count = new_tick_count
        game.save(update_fields=['tick_count'])

        gfm = GameFeedMessage.objects.create(
            game=game, message_type=GameFeedMessage.MESSAGE_TYPE_GAME_STATUS,
            message=f"skipping {player.handle}'s turn")

    game_state, _ = cq_lib.get_game_state(board)
    cq_lib.alert_game_players_to_new_move(game, game_state)
    cq_lib.push_new_game_feed_message(gfm)

    # Restart task for next player
    cycle_player_turn_if_inactive.delay(game_id, next_player_id_turn, new_tick_count)
