
from unittest.mock import patch

from itertools import chain
from collections import Counter

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from lobby.models import Player, Game
from lobby import views
from connectquatro.models import Board
from connectquatro import lib as cq_lib

class TestConnectquatroAPI(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user('testuser1@mail.com', password='password')
        self.player1 = Player.objects.create(user=self.user1, handle="foobar")
        self.user2 = User.objects.create_user('testuser2@mail.com', password='password')
        self.player2 = Player.objects.create(user=self.user2, handle="foobar")
        self.user3 = User.objects.create_user('testuser3@mail.com', password='password')
        self.player3 = Player.objects.create(user=self.user3, handle="foobar")

        self.mock_alert_game_players_to_new_move = patch.object(
            cq_lib, 'alert_game_players_to_new_move').start()

    def tearDown(self):
        self.mock_alert_game_players_to_new_move.stop()
    

    def test_player_can_drop_chip_on_empty_board_when_its_their_turn(self):
        game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, name="fooo", is_started=True, 
            max_players=2)
        self.player1.game = game
        self.player2.game = game
        self.player1.save()
        self.player2.save()
        board_state = cq_lib.board_obj_to_serialized_state({
            Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player1.id,
            Board.STATE_KEY_BOARD_LIST:[[None for i in range(7)] for j in range(7)]
        })
        board = Board.objects.create(
            game=game, board_state=board_state, board_length_x=7, board_length_y=7)

        self.client.login(username='testuser1@mail.com', password='password')
        url = reverse('api-connectquat-move')
        data = {'column_index':3}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        board.refresh_from_db()
        board_state = cq_lib.board_state_to_obj(board)
        board_list = board_state[Board.STATE_KEY_BOARD_LIST]
        self.assertEqual(board_list[6][3], self.player1.id)
        
        chip_counts = Counter()
        for row in board_list:
            for val in row:
                chip_counts[val] += 1
        self.assertEqual(chip_counts[self.player1.id], 1)
        self.assertEqual(chip_counts[None], 48)

    def test_socket_event_fires_when_a_player_makes_a_move(self):
        game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, name="fooo", is_started=True, 
            max_players=2)
        self.player1.game = game
        self.player2.game = game
        self.player1.save()
        self.player2.save()
        board_state = cq_lib.board_obj_to_serialized_state({
            Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player1.id,
            Board.STATE_KEY_BOARD_LIST:[[None for i in range(7)] for j in range(7)]
        })
        board = Board.objects.create(
            game=game, board_state=board_state, board_length_x=7, board_length_y=7)

        self.client.login(username='testuser1@mail.com', password='password')
        url = reverse('api-connectquat-move')
        data = {'column_index':3}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        alert_game_players_calls = self.mock_alert_game_players_to_new_move.call_args_list
        self.assertEqual(len(alert_game_players_calls), 1)

        self.assertEqual(alert_game_players_calls[0][0][0], game)
        passed_game_state = alert_game_players_calls[0][0][1]
        self.assertEqual(passed_game_state['board_list'][6][3], self.player1.id)
        self.assertIsNone(passed_game_state['winner'])
        self.assertFalse(passed_game_state['game_over'])
        self.assertEqual(len(passed_game_state['players']), 2)
        passed_player_slugs = [p['slug'] for p in passed_game_state['players']]
        self.assertTrue(self.player1.slug in passed_player_slugs)
        self.assertTrue(self.player2.slug in passed_player_slugs)
        self.assertEqual(passed_game_state['next_player_slug'], self.player2.slug)


    def test_player_cant_drop_chip_when_it_isnt_their_turn(self):
        game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, name="fooo", is_started=True, 
            max_players=2)
        self.player1.game = game
        self.player2.game = game
        self.player1.save()
        self.player2.save()
        board_state = cq_lib.board_obj_to_serialized_state({
            Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player2.id,
            Board.STATE_KEY_BOARD_LIST:[[None for i in range(7)] for j in range(7)]
        })
        board = Board.objects.create(
            game=game, board_state=board_state, board_length_x=7, board_length_y=7)

        self.client.login(username='testuser1@mail.com', password='password')
        url = reverse('api-connectquat-move')
        data = {'column_index':3}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue("turn order error" in response.data)
        self.mock_alert_game_players_to_new_move.assert_not_called()


    def test_player_cant_drop_chip_in_a_game_theyre_not_in(self):
        game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, name="fooo", is_started=True, 
            max_players=2)
        self.player1.game = game
        self.player2.game = game
        self.player1.save()
        self.player2.save()
        board_state = cq_lib.board_obj_to_serialized_state({
            Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player2.id,
            Board.STATE_KEY_BOARD_LIST:[[None for i in range(7)] for j in range(7)]
        })
        board = Board.objects.create(
            game=game, board_state=board_state, board_length_x=7, board_length_y=7)

        self.client.login(username='testuser3@mail.com', password='password')
        url = reverse('api-connectquat-move')
        data = {'column_index':3}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue("game not found" in response.data)
        self.mock_alert_game_players_to_new_move.assert_not_called()


    def test_player_cant_drop_chip_into_a_full_column(self):
        game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, name="fooo", is_started=True, 
            max_players=2)
        self.player1.game = game
        self.player2.game = game
        self.player1.save()
        self.player2.save()

        # Create board, where column 3 is completely filled with alternating chips.
        board_list = [[None for i in range(7)] for j in range(7)]
        for row_ix, row in enumerate(board_list):
            board_list[row_ix][3] = self.player1.id if row_ix % 2 else self.player2.id

        board_state = cq_lib.board_obj_to_serialized_state({
            Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player1.id,
            Board.STATE_KEY_BOARD_LIST:board_list
        })
        board = Board.objects.create(
            game=game, board_state=board_state, board_length_x=7, board_length_y=7)
        
        self.client.login(username='testuser1@mail.com', password='password')
        url = reverse('api-connectquat-move')
        data = {'column_index':3}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue("illegal move" in response.data)
        self.mock_alert_game_players_to_new_move.assert_not_called()


    def test_player_cant_drop_chip_into_column_off_the_board(self):
        game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, name="fooo", is_started=True, 
            max_players=2)
        self.player1.game = game
        self.player2.game = game
        self.player1.save()
        self.player2.save()
        board_state = cq_lib.board_obj_to_serialized_state({
            Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player1.id,
            Board.STATE_KEY_BOARD_LIST:[[None for i in range(7)] for j in range(7)]
        })
        board = Board.objects.create(
            game=game, board_state=board_state, board_length_x=7, board_length_y=7)

        self.client.login(username='testuser1@mail.com', password='password')
        url = reverse('api-connectquat-move')
        data = {'column_index':8} # this column doesnt exist
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue("illegal move" in response.data)
        self.mock_alert_game_players_to_new_move.assert_not_called()

    def test_active_player_and_game_tick_count_cycles_after_each_move(self):
        game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, name="fooo", is_started=True, 
            max_players=2)
        self.player1.game = game
        self.player2.game = game
        self.player3.game = game
        self.player1.turn_order = 2
        self.player2.turn_order = 3
        self.player3.turn_order = 1
        self.player1.save()
        self.player2.save()
        self.player3.save()
        game.archived_players.set([self.player1, self.player2, self.player3])

        board_state = cq_lib.board_obj_to_serialized_state({
            Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player3.id,
            Board.STATE_KEY_BOARD_LIST:[[None for i in range(7)] for j in range(7)]
        })
        board = Board.objects.create(
            game=game, board_state=board_state, board_length_x=7, board_length_y=7)

        url = reverse('api-connectquat-move')
        data = {'column_index':0}

        self.client.login(username='testuser3@mail.com', password='password')
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        board.refresh_from_db()
        game.refresh_from_db()
        board_state = cq_lib.board_state_to_obj(board)
        self.assertEqual(board_state[Board.STATE_KEY_NEXT_PLAYER_TO_ACT], self.player1.id)
        self.assertEqual(game.tick_count, 1)

        self.client.login(username='testuser1@mail.com', password='password')
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        board.refresh_from_db()
        game.refresh_from_db()
        board_state = cq_lib.board_state_to_obj(board)
        self.assertEqual(board_state[Board.STATE_KEY_NEXT_PLAYER_TO_ACT], self.player2.id)
        self.assertEqual(game.tick_count, 2)

        self.client.login(username='testuser2@mail.com', password='password')
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        board.refresh_from_db()
        game.refresh_from_db()
        board_state = cq_lib.board_state_to_obj(board)
        self.assertEqual(board_state[Board.STATE_KEY_NEXT_PLAYER_TO_ACT], self.player3.id)
        self.assertEqual(game.tick_count, 3)

    def test_player_can_win_game_by_getting_4_in_a_row(self):
        game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, name="fooo", is_started=True, 
            max_players=2)
        self.player1.game = game
        self.player2.game = game
        self.player1.save()
        self.player2.save()
        game.archived_players.set([self.player1, self.player2])
        p1 = self.player1.id
        p2 = self.player2.id
        board_list = [
            [None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None],
            [None, None, p1, p2, None, None, None],
            [None, p1, p2, p2, None, None, None],
            [p1, p2, p2, p2, None, None, None],
        ]
        board_state = cq_lib.board_obj_to_serialized_state({
            Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player1.id,
            Board.STATE_KEY_BOARD_LIST:board_list
        })
        board = Board.objects.create(
            game=game, board_state=board_state, board_length_x=7, board_length_y=7, max_to_win=4)

        self.client.login(username='testuser1@mail.com', password='password')
        url = reverse('api-connectquat-move')
        data = {'column_index':3}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(response.data['game_over'])
        self.assertTrue(
            response.data['winner'],
            {'handle':self.player1.slug, 'slug':self.player2.slug})

        alert_game_players_calls = self.mock_alert_game_players_to_new_move.call_args_list
        self.assertEqual(len(alert_game_players_calls), 1)

        self.assertEqual(alert_game_players_calls[0][0][0], game)
        passed_game_state = alert_game_players_calls[0][0][1]
        self.assertEqual(passed_game_state['winner'], {'handle':self.player1.handle, 'slug':self.player1.slug})
        self.assertTrue(passed_game_state['game_over'])
        self.assertIsNotNone(game.completedgame)
        self.assertEqual(game.completedgame.winners.count(), 1)
        self.assertEqual(game.completedgame.winners.first(), self.player1)
