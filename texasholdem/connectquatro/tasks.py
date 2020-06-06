
import time

from texasholdem.celery_conf import app

@app.task
def cycle_player_turn_if_inactive(player, current_tick_count, delay):
    time.sleep(delay)
    
