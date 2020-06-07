
from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from lobby.models import Player, Game, GameFeedMessage
from connectquatro.models import Board
from connectquatro import lib as cq_lib
from connectquatro import tasks as cq_tasks

class TestConnectQuatroDropChip(APITestCase):

    def setUp(self):
        self.user1 = User.objects.create_user('testuser1@mail.com', password='password')
        self.player1 = Player.objects.create(user=self.user1, handle="foobar")
        self.user2 = User.objects.create_user('testuser2@mail.com', password='password')
        self.player2 = Player.objects.create(user=self.user2, handle="foobar")
        self.user3 = User.objects.create_user('testuser3@mail.com', password='password')
        self.player3 = Player.objects.create(user=self.user3, handle="foobar")

        self.mock_push_new_game_feed_message = patch.object(
            cq_lib, 'push_new_game_feed_message').start()
        self.mock_alert_game_players_to_new_move = patch.object(
            cq_lib, 'alert_game_players_to_new_move').start()

    def tearDown(self):
        self.mock_push_new_game_feed_message.stop()
        self.mock_alert_game_players_to_new_move.stop()
    
    def test_cycle_player_turn_if_inactive_updates_active_player(self):
        game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, name="fooo",
            is_started=True, is_over=False, max_players=2)
        self.player1.game = game
        self.player1.turn_order = 1
        self.player2.game = game
        self.player2.turn_order = 2
        self.player1.save()
        self.player2.save()
        board_state = cq_lib.board_obj_to_serialized_state({
            Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player1.id,
            Board.STATE_KEY_BOARD_LIST:[[None for i in range(7)] for j in range(7)]
        })
        board = Board.objects.create(
            game=game, board_state=board_state, board_length_x=7, board_length_y=7)
        
        # Run the task
        cq_tasks.cycle_player_turn_if_inactive(
            game.id, self.player1.id, 0)
        
        game.refresh_from_db()
        board.refresh_from_db()
        active_player_id = cq_lib.get_active_player_id_from_board(board)
        self.assertEqual(active_player_id, self.player2.id)


    def test_cycle_player_turn_if_inactive_creates_game_feed_message(self):
        game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, name="fooo",
            is_started=True, is_over=False, max_players=2)
        self.player1.game = game
        self.player1.turn_order = 1
        self.player2.game = game
        self.player2.turn_order = 2
        self.player1.save()
        self.player2.save()
        board_state = cq_lib.board_obj_to_serialized_state({
            Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player1.id,
            Board.STATE_KEY_BOARD_LIST:[[None for i in range(7)] for j in range(7)]
        })
        board = Board.objects.create(
            game=game, board_state=board_state, board_length_x=7, board_length_y=7)
        
        self.assertEqual(GameFeedMessage.objects.count(), 0)

        # Run the task
        cq_tasks.cycle_player_turn_if_inactive(
            game.id, self.player1.id, 0)

        self.assertEqual(GameFeedMessage.objects.count(), 1)
        gfm = GameFeedMessage.objects.first()
        self.assertEqual(gfm.game, game)
        self.assertEqual(gfm.message_type, GameFeedMessage.MESSAGE_TYPE_GAME_STATUS)
        self.mock_push_new_game_feed_message.assert_called_once_with(gfm)
        self.mock_alert_game_players_to_new_move.assert_called_once()
