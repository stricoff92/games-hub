
def get_user_player_game(request) -> tuple:
    user = request.user
    player = user.player
    game = player.game
    return user, player, game
