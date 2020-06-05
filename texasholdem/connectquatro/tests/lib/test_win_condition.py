

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from lobby.models import Player, Game
from lobby import views
from connectquatro.models import Board
from connectquatro import lib as cq_lib

class TestConnectQuatroWinConditions(APITestCase):
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


    def tearDown(self):
        pass
    

    def test_no_win_conditions_for_connect_quatro_board(self):
        self.board.board_state = cq_lib.board_obj_to_serialized_state({
            Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player1.id,
            Board.STATE_KEY_BOARD_LIST: [
                [None for i in range(7)] for j in range(7)
            ]
        })
        self.board.save()
        self.assertIsNone(cq_lib.get_winning_player(self.board))

        self.board.board_state = cq_lib.board_obj_to_serialized_state({
            Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player1.id,
            Board.STATE_KEY_BOARD_LIST: [
                [None for i in range(7)],
                [None for i in range(7)],
                [None for i in range(7)],
                [None for i in range(7)],
                [None for i in range(7)],
                [None for i in range(7)],
                [
                    self.player2.id, # 3/4 in a row
                    self.player2.id, #
                    self.player2.id, #
                    self.player1.id,
                    self.player2.id, 
                    None, None],
            ]
        })
        self.board.save()
        self.assertIsNone(cq_lib.get_winning_player(self.board))

        self.board.board_state = cq_lib.board_obj_to_serialized_state({
            Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player1.id,
            Board.STATE_KEY_BOARD_LIST: [
                [None for i in range(7)],
                [None for i in range(7)],
                [None for i in range(7)],
                [None for i in range(7)],
                [self.player1.id, None, None, None, None, None, None], # 3/4 in a row
                [self.player1.id, None, None, None, None, None, None], #
                [self.player1.id, None, None, None, None, None, None], # 
            ]})
        self.board.save()
        self.assertIsNone(cq_lib.get_winning_player(self.board))

        self.board.board_state = cq_lib.board_obj_to_serialized_state({
            Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player1.id,
            Board.STATE_KEY_BOARD_LIST: [
                [None for i in range(7)],
                [None for i in range(7)],
                [None for i in range(7)],
                [None, None, None, None, None, None, None],
                [None, self.player1.id, None, None, None, None, None], # 3/4 in a row
                [None, None, self.player1.id, None, None, None, None], #
                [None, None, None, self.player1.id, None, None, None], #
            ]})
        self.board.save()
        self.assertIsNone(cq_lib.get_winning_player(self.board))

        self.board.board_state = cq_lib.board_obj_to_serialized_state({
            Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player1.id,
            Board.STATE_KEY_BOARD_LIST: [
                [None for i in range(7)],
                [None for i in range(7)],
                [None for i in range(7)],
                [None for i in range(7)],
                [None, None, None, None, None, self.player1.id, None], # 3/4 in a row
                [None, None, None, None, self.player1.id, None, None], #
                [None, None, None, self.player1.id, None, None, None], #
            ]})
        self.board.save()
        self.assertIsNone(cq_lib.get_winning_player(self.board))


    def test_horizontal_win_conditions_for_connect_quatro_board(self):
        self.game.archived_players.set([self.player2])
        self.board.board_state = cq_lib.board_obj_to_serialized_state({
            Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player1.id,
            Board.STATE_KEY_BOARD_LIST: [
                [None for i in range(7)],
                [None for i in range(7)],
                [None for i in range(7)],
                [None for i in range(7)],
                [None for i in range(7)],
                [None for i in range(7)],
                [
                    self.player2.id, # 4 in a row
                    self.player2.id, #
                    self.player2.id, #
                    self.player2.id, #
                    None, None, None
                ],
            ]
        })
        self.board.save()
        self.assertEqual(cq_lib.get_winning_player(self.board), self.player2)

    def test_verticle_win_conditions_for_connect_quatro_board(self):
        self.game.archived_players.set([self.player1])
        self.board.board_state = cq_lib.board_obj_to_serialized_state({
            Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player1.id,
            Board.STATE_KEY_BOARD_LIST: [
                [None for i in range(7)],
                [None for i in range(7)],
                [None for i in range(7)],
                [self.player1.id, None, None, None, None, None, None], # 4 in a row
                [self.player1.id, None, None, None, None, None, None], #
                [self.player1.id, None, None, None, None, None, None], #
                [self.player1.id, None, None, None, None, None, None], #
            ]})
        self.board.save()
        self.assertEqual(cq_lib.get_winning_player(self.board), self.player1)


    def test_diagonal_win_conditions_for_connect_quatro_board(self):
        self.board.board_state = cq_lib.board_obj_to_serialized_state({
            Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player1.id,
            Board.STATE_KEY_BOARD_LIST: [
                [None for i in range(7)],
                [None for i in range(7)],
                [None for i in range(7)],
                [self.player1.id, None, None, None, None, None, None], # 4/4 in a row
                [None, self.player1.id, None, None, None, None, None], #
                [None, None, self.player1.id, None, None, None, None], #
                [None, None, None, self.player1.id, None, None, None], #
            ]})
        self.board.save()
        self.game.archived_players.set([self.player1, self.player2])
        self.assertEqual(cq_lib.get_winning_player(self.board), self.player1)

        self.board.board_state = cq_lib.board_obj_to_serialized_state({
            Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player1.id,
            Board.STATE_KEY_BOARD_LIST: [
                [None for i in range(7)],
                [None for i in range(7)],
                [None for i in range(7)],
                [None, None, None, None, None, None, self.player2.id], # 4/4 in a row
                [None, None, None, None, None, self.player2.id, None], #
                [None, None, None, None, self.player2.id, None, None], #
                [None, None, None, self.player2.id, None, None, None], #
            ]})
        self.board.save()
        self.assertEqual(cq_lib.get_winning_player(self.board), self.player2)