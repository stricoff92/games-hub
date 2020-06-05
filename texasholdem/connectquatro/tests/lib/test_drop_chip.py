

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from lobby.models import Player, Game
from lobby import views
from connectquatro.models import Board
from connectquatro import lib as cq_lib

class TestConnectQuatroDropChip(APITestCase):
    def setUp(self):
        self.game = Game.objects.create(
            name="foobar", game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT,
            is_started=True, max_players=2)
        self.board = Board.objects.create(
            game=self.game, max_to_win=4, board_length_x=7, board_length_y=7)

        self.user1 = User.objects.create_user('testuser1@mail.com', password='password')
        self.player1 = Player.objects.create(user=self.user1, handle="foobar", game=self.game)
        self.user2 = User.objects.create_user('testuser2@mail.com', password='password')
        self.player2 = Player.objects.create(user=self.user2, handle="foobar", game=self.game)

        self.board.board_state = cq_lib.board_obj_to_serialized_state({
                    Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player1.id,
                    Board.STATE_KEY_BOARD_LIST: [
                        [None for i in range(7)] for j in range(7)
                    ]
                })

    def test_drop_chip_empty_board(self):
        cq_lib.drop_chip(self.board, self.player1, 3)
        self.board.refresh_from_db()
        board_state = cq_lib.board_state_to_obj(self.board)
        board_list = board_state[Board.STATE_KEY_BOARD_LIST]
        self.assertTrue(board_list[6][3], self.player1.id)

        cq_lib.drop_chip(self.board, self.player2, 3)
        self.board.refresh_from_db()
        board_state = cq_lib.board_state_to_obj(self.board)
        board_list = board_state[Board.STATE_KEY_BOARD_LIST]
        self.assertTrue(board_list[6][3], self.player1.id)
        self.assertTrue(board_list[5][3], self.player2.id)
                
    def test_drop_chip_in_full_column(self):
        self.board.board_state = cq_lib.board_obj_to_serialized_state({
                    Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player1.id,
                    Board.STATE_KEY_BOARD_LIST: [
                        [None, 1, None, None, None, None, None],
                        [None, 2, None, None, None, None, None],
                        [None, 1, None, None, None, None, None],
                        [None, 1, None, None, None, None, None],
                        [None, 2, None, None, None, None, None],
                        [None, 1, None, None, None, None, None],
                        [None, 1, None, None, None, None, None],
                    ]
                })
        self.assertRaises(
            cq_lib.ColumnIsFullError,
            lambda: cq_lib.drop_chip(self.board, self.player2, 1))

    def test_drop_chip_in_column_off_board(self):
        self.board.board_state = cq_lib.board_obj_to_serialized_state({
                    Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player1.id,
                    Board.STATE_KEY_BOARD_LIST: [
                        [None, None, None, None, None, None, None],
                        [None, None, None, None, None, None, None],
                        [None, None, None, None, None, None, None],
                        [None, None, None, None, None, None, None],
                        [None, None, None, None, None, None, None],
                        [None, None, None, None, None, None, None],
                        [None, None, None, None, None, None, None],
                    ]
                })
        self.assertRaises(
            cq_lib.ColumnOutOfRangeError,
            lambda: cq_lib.drop_chip(self.board, self.player2, 8))
