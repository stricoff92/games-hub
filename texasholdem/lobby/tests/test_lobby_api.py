
from unittest.mock import patch, Mock

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from lobby.models import Player, Game, CompletedGame
from lobby import views
from lobby import lib as lobby_lib
from connectquatro.models import Board
from connectquatro import lib as cq_lib

class TestLobbyTest(APITestCase):

    def setUp(self):
        self.user1 = User.objects.create_user('testuser1@mail.com', password='password')
        self.player1 = Player.objects.create(user=self.user1, handle="foobar")

        self.mock_update_lobby_list_add_connect_quatro = patch.object(
            lobby_lib, 'update_lobby_list_add_connect_quatro').start()
        self.mock_update_lobby_list_remove_game = patch.object(
            lobby_lib, 'update_lobby_list_remove_game').start()
        self.mock_update_lobby_list_player_count = patch.object(
            lobby_lib, 'update_lobby_list_player_count').start()
        self.mock_push_player_quit_game_event = patch.object(
            lobby_lib, 'push_player_quit_game_event').start()
        self.mock_push_player_promoted_to_lobby_leader = patch.object(
            lobby_lib, 'push_player_promoted_to_lobby_leader').start()
        self.mock_alert_game_lobby_game_started = patch.object(
            cq_lib, 'alert_game_lobby_game_started').start()
        self.mock_alert_game_players_to_new_move = patch.object(
            cq_lib, 'alert_game_players_to_new_move').start()

    def tearDown(self):
        self.mock_update_lobby_list_add_connect_quatro.stop()
        self.mock_update_lobby_list_remove_game.stop()
        self.mock_alert_game_lobby_game_started.stop()
        self.mock_push_player_quit_game_event.stop()
        self.mock_update_lobby_list_player_count.stop()
        self.mock_push_player_promoted_to_lobby_leader.stop()
    

    def test_player_not_in_a_lobby_can_see_the_lobby_list(self):

        self.client.login(username='testuser1@mail.com', password='password')
        
        # Joinable games
        game1 = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT,
            is_public=True, is_started=False)
        game2 = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT,
            is_public=True, is_started=False)
        
        # Non joinable games
        Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT,
            is_public=False, is_started=False)
        Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT,
            is_public=True, is_started=True)
        Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT,
            is_public=True, is_started=True)

        url = reverse('api-lobby-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_slugs = [g['slug'] for g in response.data]
        self.assertEqual(len(returned_slugs), 2)
        self.assertTrue(game1.slug in returned_slugs)
        self.assertTrue(game2.slug in returned_slugs)


    def test_player_can_create_a_public_game(self):
        """ Test player can create a game.
        """
        self.client.login(username='testuser1@mail.com', password='password')
        data = {
            'roomtype':Game.GAME_TYPE_CHOICE_CONNECT_QUAT,
            'roomname':'foo0 barR',
            'boarddimx':8,
            'boarddimy':9,
            'boardplayercount':2,
            'boardwincount':5,
            'privacy':'public',
        }
        url = reverse('api-lobby-create')
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        game = Game.objects.get(id=response.data['id'])
        board = Board.objects.get(game=game)
        self.player1.refresh_from_db()
        self.assertEqual(game.players.count(), 1)
        self.assertEqual(game.players.first(), self.player1)
        self.assertEqual(game.name, 'foo0 barR')
        self.assertEqual(game.game_type, Game.GAME_TYPE_CHOICE_CONNECT_QUAT)
        self.assertEqual(game.tick_count, 0)
        self.assertTrue(game.is_public)
        self.assertEqual(self.player1.game, game)
        self.assertTrue(self.player1.is_lobby_owner)
        self.assertEqual(game.max_players, 2)
        self.assertEqual(board.max_to_win, 5)
        self.assertEqual(board.board_length_x, 8)
        self.assertEqual(board.board_length_y, 9)
        self.assertIsNotNone(game.join_game_id)

        # test socket event fires
        self.mock_update_lobby_list_add_connect_quatro.assert_called_once_with(game, board)

    def test_player_can_create_a_private_game(self):
        """ Test player can create private a game.
        """
        self.client.login(username='testuser1@mail.com', password='password')
        data = {
            'roomtype':Game.GAME_TYPE_CHOICE_CONNECT_QUAT,
            'roomname':'foo0 barR',
            'boarddimx':8,
            'boarddimy':9,
            'boardplayercount':2,
            'boardwincount':5,
            'privacy':'private',
        }
        url = reverse('api-lobby-create')
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        game = Game.objects.get(id=response.data['id'])
        board = Board.objects.get(game=game)
        self.player1.refresh_from_db()
    
        self.assertEqual(game.players.count(), 1)
        self.assertEqual(game.players.first(), self.player1)
        self.assertEqual(game.name, 'foo0 barR')
        self.assertEqual(game.game_type, Game.GAME_TYPE_CHOICE_CONNECT_QUAT)
        self.assertFalse(game.is_public)
        self.assertEqual(game.max_players, 2)
        self.assertEqual(game.tick_count, 0)
        self.assertIsNotNone(game.join_game_id)

        self.assertEqual(self.player1.game, game)
        self.assertTrue(self.player1.is_lobby_owner)

        self.assertEqual(board.max_to_win, 5)
        self.assertEqual(board.board_length_x, 8)
        self.assertEqual(board.board_length_y, 9)
        
        self.mock_update_lobby_list_add_connect_quatro.assert_not_called()


    def test_anonymous_player_cannot_create_a_game(self):
        """ Test anon user cannot create a game.
        """
        data = {
            'roomtype':Game.GAME_TYPE_CHOICE_CONNECT_QUAT,
            'roomname':'foo0 barR',
            'boarddimx':8,
            'boarddimy':9,
            'boardplayercount':2,
            'boardwincount':5,
            'privacy':'public',
        }
        url = reverse('api-lobby-create')
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    def test_player_cant_create_a_game_if_already_in_a_game(self):
        """ Test player cant create a game if they're already in one.
        """
        self.client.login(username='testuser1@mail.com', password='password')

        other_game = Game.objects.create(game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, name="foo")
        self.player1.game = other_game
        self.player1.save(update_fields=['game'])

        data = {
            'roomtype':Game.GAME_TYPE_CHOICE_CONNECT_QUAT,
            'roomname':'foo0 barR',
            'boarddimx':8,
            'boarddimy':9,
            'boardplayercount':2,
            'boardwincount':5,
            'privacy':'public',
        }
        url = reverse('api-lobby-create')
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_player_can_start_connect_quatro_with_enough_players_game(self):
        """ Test player can start a game with 2+ players.
        """
        self.client.login(username='testuser1@mail.com', password='password')

        self.user2 = User.objects.create_user('testuser2@mail.com', password='password')
        self.player2 = Player.objects.create(user=self.user2, handle="foobar")
        game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT,
            name="foo", is_started=False, max_players=2)
        board = Board.objects.create(
            game=game, board_length_x=7,board_length_y=7)
        
        self.player1.game = game
        self.player1.is_lobby_owner = True
        self.player1.save()
        self.player2.game = game
        self.player2.save()

        url = reverse("api-lobby-start")
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        game.refresh_from_db()
        board.refresh_from_db()
        self.player2.refresh_from_db()
        self.player1.refresh_from_db()

        self.assertTrue(game.is_started)
        self.assertTrue(self.player1 in game.archived_players.all())
        self.assertTrue(self.player2 in game.archived_players.all())
        self.assertIsNotNone(self.player1.turn_order)
        self.assertIsNotNone(self.player2.turn_order)
        self.assertNotEqual(self.player1.turn_order, self.player2.turn_order)
        self.assertIsNotNone(self.player1.color)
        self.assertIsNotNone(self.player2.color)
        self.assertNotEqual(self.player1.color, self.player2.color)
        self.assertEqual(self.player1.lobby_status, Player.LOBBY_STATUS_JOINED)
        self.assertEqual(self.player2.lobby_status, Player.LOBBY_STATUS_JOINED)

        board_state = cq_lib.board_state_to_obj(board)
        board_list = board_state[Board.STATE_KEY_BOARD_LIST]
        self.assertEqual(len(board_list), 7)
        for row in board_list:
            self.assertEqual(len(row), 7)
            self.assertFalse(any(row))
        
        self.mock_alert_game_lobby_game_started.assert_called_once_with(game)
        self.mock_update_lobby_list_remove_game.assert_called_once_with(game)


    def test_player_cannot_start_with_1_player(self):
        """ Test player cannot start a game if they're the only one in the room
        """
        self.client.login(username='testuser1@mail.com', password='password')

        game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT,
            name="foo", is_started=False, max_players=2)
        board = Board.objects.create(
            game=game, board_length_x=7,board_length_y=7)
        
        self.player1.game = game
        self.player1.is_lobby_owner = True
        self.player1.save()

        url = reverse("api-lobby-start")
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.mock_alert_game_lobby_game_started.assert_not_called()
        self.mock_update_lobby_list_remove_game.assert_not_called()


    def test_player_cant_start_game_if_theyre_not_in_a_game(self):
        """ Test player cannot start a game if they're not lobby owner.
        """
        self.client.login(username='testuser1@mail.com', password='password')

        self.user2 = User.objects.create_user('testuser2@mail.com', password='password')
        self.player2 = Player.objects.create(user=self.user2, handle="foobar")
        game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT,
            name="foo", is_started=False, max_players=2)
        board = Board.objects.create(
            game=game, board_length_x=7,board_length_y=7)
        
        self.player1.game = None
        self.player1.save()
        self.player2.game = game
        self.player2.save()

        url = reverse("api-lobby-start")
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.mock_alert_game_lobby_game_started.assert_not_called()
        self.mock_update_lobby_list_remove_game.assert_not_called()


    def test_player_cant_start_game_if_theyre_not_lobby_owner(self):
        """ Test player cannot start a game if they're not lobby owner.
        """
        self.client.login(username='testuser1@mail.com', password='password')

        self.user2 = User.objects.create_user('testuser2@mail.com', password='password')
        self.player2 = Player.objects.create(user=self.user2, handle="foobar")
        game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT,
            name="foo", is_started=False, max_players=2)
        board = Board.objects.create(
            game=game, board_length_x=7,board_length_y=7)
        
        self.player1.game = game
        self.player1.is_lobby_owner = False
        self.player1.save()
        self.player2.game = game
        self.player2.save()

        url = reverse("api-lobby-start")
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.mock_alert_game_lobby_game_started.assert_not_called()
        self.mock_update_lobby_list_remove_game.assert_not_called()


    def test_player_can_join_a_lobby_which_then_becomes_full(self):
        """ Test player can join a game
        """
        self.client.login(username='testuser1@mail.com', password='password')

        other_game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, max_players=2)
        
        # Add a player to the game
        user2 = User.objects.create_user('testuser2@mail.com', password='password')
        player2 = Player.objects.create(user=user2, handle="foobar2")
        player2.game = other_game
        player2.save()
        self.assertEqual(other_game.players.count(), 1)

        url = reverse('api-lobby-join', kwargs={'slug':other_game.slug})
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.player1.refresh_from_db()
        self.assertEqual(other_game.players.count(), 2)
        self.assertEqual(self.player1.game, other_game)
        self.assertFalse(self.player1.is_lobby_owner)

        self.mock_update_lobby_list_remove_game.assert_called_once_with(
            other_game)
        self.mock_update_lobby_list_player_count.assert_not_called()

    def test_player_can_join_a_lobby_which_is_still_not_full(self):
        """ Test player can join a game
        """
        self.client.login(username='testuser1@mail.com', password='password')

        other_game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, max_players=3)
        
        # Add a player to the game
        user2 = User.objects.create_user('testuser2@mail.com', password='password')
        player2 = Player.objects.create(user=user2, handle="foobar2")
        player2.game = other_game
        player2.save()
        self.assertEqual(other_game.players.count(), 1)

        url = reverse('api-lobby-join', kwargs={'slug':other_game.slug})
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.player1.refresh_from_db()
        self.assertEqual(other_game.players.count(), 2)
        self.assertEqual(self.player1.game, other_game)
        self.assertFalse(self.player1.is_lobby_owner)

        self.mock_update_lobby_list_player_count.assert_called_once_with(
            other_game, 2)
        self.mock_update_lobby_list_remove_game.assert_not_called()


    def test_player_cant_join_a_full_lobby(self):
        """ Test player cant join a full game
        """
        self.client.login(username='testuser1@mail.com', password='password')

        other_game = Game.objects.create(
            name="foo",
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT,
            max_players=2)

        user2 = User.objects.create_user('testuser2@mail.com', password='password')
        player2 = Player.objects.create(user=user2, handle="foobar2")
        user3 = User.objects.create_user('testuser3@mail.com', password='password')
        player3 = Player.objects.create(user=user3, handle="foobar3")
        player2.game = other_game
        player2.save()
        player3.game = other_game
        player3.save()

        url = reverse('api-lobby-join', kwargs={'slug':other_game.slug})
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.mock_update_lobby_list_player_count.assert_not_called()
        self.mock_update_lobby_list_remove_game.assert_not_called()


    def test_player_cant_join_a_started_game(self):
        """ Test player cant join a started game
        """
        self.client.login(username='testuser1@mail.com', password='password')

        other_game = Game.objects.create(
            name="foo",
            is_started=True,
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT)
        url = reverse('api-lobby-join', kwargs={'slug':other_game.slug})
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_player_cant_join_a_game_if_already_in_a_game(self):
        """ Test player cant join a game if they're already in one.
        """
        self.client.login(username='testuser1@mail.com', password='password')

        other_game = Game.objects.create(game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, name="foo")
        self.player1.game = other_game
        self.player1.save(update_fields=['game'])

        yet_another_other_game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT)
        url = reverse('api-lobby-join', kwargs={'slug':yet_another_other_game.slug})
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_player_cant_join_pirvate_game_with_no_join_id_or_invalid_join_id(self):
        """ Test player cant join a private game without a join id
        """
        self.user2 = User.objects.create_user('testuser2@mail.com', password='password')
        self.player2 = Player.objects.create(user=self.user2, handle="foobar")
        other_game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, name="foo", is_started=False, is_public=False,
            join_game_id="12345678", max_players=3)

        self.player1.game = other_game
        self.player1.save(update_fields=['game'])

        self.client.login(username='testuser2@mail.com', password='password')
        url = reverse('api-lobby-join', kwargs={'slug':other_game.slug})

        # Missing join id
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue("join_game_id is required for private game" in response.data)

        # Invalid join id
        response = self.client.post(url, {'join_game_id':'gggggggg'}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue("invalid join_game_id" in response.data)

    def test_player_can_join_pirvate_game_with_join_id(self):
        """ Test player can join game with a join id
        """
        self.user2 = User.objects.create_user('testuser2@mail.com', password='password')
        self.player2 = Player.objects.create(user=self.user2, handle="foobar")

        other_game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, name="foo", is_started=False, is_public=False,
            join_game_id="12345678", max_players=3)
        self.player1.game = other_game
        self.player1.save(update_fields=['game'])

        self.client.login(username='testuser2@mail.com', password='password')
        url = reverse('api-lobby-join', kwargs={'slug':other_game.slug})
        response = self.client.post(url, {'join_game_id':'12345678'}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.player2.refresh_from_db()
        self.assertEqual(self.player2.game, other_game)

    def test_lobby_list_not_updated_when_user_joins_private_lobby(self):
        """ Test lobby list isnt updated when a player joins a private lobby
        """
        self.user2 = User.objects.create_user('testuser2@mail.com', password='password')
        self.player2 = Player.objects.create(user=self.user2, handle="foobar")

        other_game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, name="foo", is_started=False, is_public=False,
            join_game_id="12345678", max_players=3)
        self.player1.game = other_game
        self.player1.save(update_fields=['game'])

        self.client.login(username='testuser2@mail.com', password='password')
        url = reverse('api-lobby-join', kwargs={'slug':other_game.slug})
        response = self.client.post(url, {'join_game_id':'12345678'}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.mock_update_lobby_list_remove_game.assert_not_called()
        self.mock_update_lobby_list_player_count.assert_not_called()

 
    def test_player_can_leave_a_game_lobby_that_was_full_and_not_Started(self):
        """ Test player can leave a not started game what was full
            
        """
        self.user2 = User.objects.create_user('testuser2@mail.com', password='password')
        self.player2 = Player.objects.create(user=self.user2, handle="duuude")

        game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, name="foo", max_players=2)
        board = Board.objects.create(game=game)
        game_id = game.id
        self.player1.game = game
        self.player2.game = game
        self.player1.save(update_fields=['game'])
        self.player2.save(update_fields=['game'])
        self.assertEqual(game.players.count(), 2)

        self.client.login(username='testuser1@mail.com', password='password')
        url = reverse('api-lobby-leave')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.player1.refresh_from_db()
        self.assertTrue(Game.objects.filter(id=game_id).exists())
        self.assertTrue(self.player1 not in game.players.all())
        self.assertTrue(self.player2 in game.players.all())
        self.assertEqual(game.players.count(), 1)
        self.mock_push_player_quit_game_event.assert_called_once_with(game, self.player1)
        self.mock_update_lobby_list_player_count.assert_not_called()
        self.mock_update_lobby_list_remove_game.assert_not_called()
        self.mock_update_lobby_list_add_connect_quatro.assert_called_once_with(game, board)

    def test_lobby_leadership_is_passed_when_lobby_leader_leaves_an_unstarted_game(self):
        """ Test lobby leadership is passed to a new player when the leader leaves
            
        """
        self.user2 = User.objects.create_user('testuser2@mail.com', password='password')
        self.player2 = Player.objects.create(user=self.user2, handle="duuude")

        game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, name="foo", max_players=2, is_started=False)
        board = Board.objects.create(game=game)
        game_id = game.id
        self.player1.game = game
        self.player1.is_lobby_owner = True
        self.player2.game = game
        self.player1.save(update_fields=['game', 'is_lobby_owner'])
        self.player2.save(update_fields=['game'])
        self.assertEqual(game.players.count(), 2)

        self.client.login(username='testuser1@mail.com', password='password')
        url = reverse('api-lobby-leave')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.player1.refresh_from_db()
        self.player2.refresh_from_db()
        self.assertTrue(Game.objects.filter(id=game_id).exists())
        self.assertTrue(self.player1 not in game.players.all())
        self.assertTrue(self.player2 in game.players.all())
        self.assertEqual(game.players.count(), 1)
        self.assertTrue(self.player2.is_lobby_owner)
        self.assertFalse(self.player1.is_lobby_owner)
    
        self.mock_push_player_quit_game_event.assert_called_once_with(game, self.player1)
        self.mock_update_lobby_list_add_connect_quatro.assert_called_once_with(game, board)
        self.mock_push_player_promoted_to_lobby_leader.assert_called_once_with(self.player2, game)
        self.mock_update_lobby_list_player_count.assert_not_called()
        self.mock_update_lobby_list_remove_game.assert_not_called()


    def test_lobby_leadership_is_not_passed_when_non_lobby_leader_leaves(self):
        """ Test lobby leadership isnt passed to anyone when a non leader leaves
        """
        self.user2 = User.objects.create_user('testuser2@mail.com', password='password')
        self.player2 = Player.objects.create(user=self.user2, handle="duuude")

        game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, name="foo", max_players=2, is_started=False)
        board = Board.objects.create(game=game)
        game_id = game.id
        self.player1.game = game
        self.player1.is_lobby_owner = True
        self.player2.game = game
        self.player1.save(update_fields=['game', 'is_lobby_owner'])
        self.player2.save(update_fields=['game'])
        self.assertEqual(game.players.count(), 2)

        self.client.login(username='testuser2@mail.com', password='password')
        url = reverse('api-lobby-leave')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.player1.refresh_from_db()
        self.player2.refresh_from_db()
        self.assertTrue(Game.objects.filter(id=game_id).exists())
        self.assertTrue(self.player1 in game.players.all())
        self.assertTrue(self.player2 not in game.players.all())
        self.assertEqual(game.players.count(), 1)
        self.assertTrue(self.player1.is_lobby_owner)
        self.assertFalse(self.player2.is_lobby_owner)
    
        self.mock_push_player_promoted_to_lobby_leader.assert_not_called()
        self.mock_push_player_quit_game_event.assert_called_once_with(game, self.player2)
        self.mock_update_lobby_list_add_connect_quatro.assert_called_once_with(game, board)
        
        self.mock_update_lobby_list_player_count.assert_not_called()
        self.mock_update_lobby_list_remove_game.assert_not_called()


    def test_player_can_leave_a_unstarted_game_lobby_that_was_not_full(self):
        """ Test player can leave a game, game not deleted
        """
        self.user2 = User.objects.create_user('testuser2@mail.com', password='password')
        self.player2 = Player.objects.create(user=self.user2, handle="duuude")

        game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, name="foo", max_players=3)
        board = Board.objects.create(game=game)
        game_id = game.id
        self.player1.game = game
        self.player2.game = game
        self.player1.save(update_fields=['game'])
        self.player2.save(update_fields=['game'])
        self.assertEqual(game.players.count(), 2)

        self.client.login(username='testuser1@mail.com', password='password')
        url = reverse('api-lobby-leave')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.player1.refresh_from_db()
        self.assertTrue(Game.objects.filter(id=game_id).exists())
        self.assertTrue(self.player1 not in game.players.all())
        self.assertTrue(self.player2 in game.players.all())
        self.assertEqual(game.players.count(), 1)
        self.mock_push_player_quit_game_event.assert_called_once_with(game, self.player1)
        self.mock_update_lobby_list_player_count.assert_called_once_with(game, 1)
        self.mock_update_lobby_list_remove_game.assert_not_called()
        self.mock_update_lobby_list_add_connect_quatro.assert_not_called()


    def test_player_can_leave_an_unstarted_game_no_one_else_left_in_the_room(self):
        """ Test player can leave a game, game is deleted if last player leaves and the game never started
        """
        self.client.login(username='testuser1@mail.com', password='password')

        game = Game.objects.create(game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT)
        game_id = game.id
        self.player1.game = game
        self.player1.save(update_fields=['game'])

        url = reverse('api-lobby-leave')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.player1.refresh_from_db()
        self.assertIsNone(self.player1.game)
        self.assertFalse(Game.objects.filter(id=game_id).exists())
        self.mock_update_lobby_list_remove_game.assert_called_once()


    def test_player_can_leave_a_started_connect_quatrogame_still_others_left_in_the_game(self):
        """ Test player can leave a started game that will still have > 1 players leftover.
        """
        self.user2 = User.objects.create_user('testuser2@mail.com', password='password')
        self.player2 = Player.objects.create(user=self.user2, handle="duuude")
        self.user3 = User.objects.create_user('testuser3@mail.com', password='password')
        self.player3 = Player.objects.create(user=self.user3, handle="yoo-duuuude")

        game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, name="foo", max_players=3,
            is_started=True, is_over=False)
        board_state = cq_lib.board_obj_to_serialized_state({
            Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player1.id,
            Board.STATE_KEY_BOARD_LIST:[[None for i in range(7)] for j in range(7)]
        })
        board = Board.objects.create(game=game, board_state=board_state)
        game_id = game.id
        self.player1.game = game
        self.player2.game = game
        self.player3.game = game
        self.player1.save(update_fields=['game'])
        self.player2.save(update_fields=['game'])
        self.player3.save(update_fields=['game'])
        self.assertEqual(game.players.count(), 3)

        self.client.login(username='testuser1@mail.com', password='password')
        url = reverse('api-lobby-leave')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        game.refresh_from_db()
        self.player1.refresh_from_db()
        self.assertTrue(Game.objects.filter(id=game_id).exists())
        self.assertFalse(game.is_over)
        self.assertTrue(self.player1 not in game.players.all())
        self.assertTrue(self.player2 in game.players.all())
        self.assertTrue(self.player3 in game.players.all())
        self.assertEqual(game.players.count(), 2)

        self.mock_push_player_quit_game_event.assert_not_called()
        self.mock_update_lobby_list_player_count.assert_not_called()
        self.mock_update_lobby_list_remove_game.assert_not_called()
        self.mock_update_lobby_list_add_connect_quatro.assert_not_called()

        calls = self.mock_alert_game_players_to_new_move.call_args_list
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0][0], game)

        passed_game_state = calls[0][0][1]
        self.assertFalse(passed_game_state['game_over'])
        self.assertTrue(
            passed_game_state['next_player_slug'] in [self.player2.slug], self.player3.slug)
        self.assertEqual(len(passed_game_state['players']), 2)
        passed_player_slugs = [p['slug'] for p in passed_game_state['players']]
        self.assertTrue(self.player2.slug in passed_player_slugs)
        self.assertTrue(self.player3.slug in passed_player_slugs)
        self.assertFalse(CompletedGame.objects.filter(game=game).exists())


    def test_player_can_leave_a_started_connect_quatrogame_only_1_player_left(self):
        """ Test player can leave a started game that will only have 1 players leftover.
        """
        self.user2 = User.objects.create_user('testuser2@mail.com', password='password')
        self.player2 = Player.objects.create(user=self.user2, handle="duuude")


        game = Game.objects.create(
            game_type=Game.GAME_TYPE_CHOICE_CONNECT_QUAT, name="foo", max_players=3,
            is_started=True, is_over=False)
        board_state = cq_lib.board_obj_to_serialized_state({
            Board.STATE_KEY_NEXT_PLAYER_TO_ACT:self.player1.id,
            Board.STATE_KEY_BOARD_LIST:[[None for i in range(7)] for j in range(7)]
        })
        board = Board.objects.create(game=game, board_state=board_state)
        game_id = game.id
        self.player1.game = game
        self.player2.game = game
        self.player1.save(update_fields=['game'])
        self.player2.save(update_fields=['game'])
        self.assertEqual(game.players.count(), 2)

        self.client.login(username='testuser1@mail.com', password='password')
        url = reverse('api-lobby-leave')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        game.refresh_from_db()
        self.player1.refresh_from_db()
        self.assertTrue(Game.objects.filter(id=game_id).exists())
        self.assertTrue(game.is_over)
        self.assertTrue(self.player1 not in game.players.all())
        self.assertTrue(self.player2 in game.players.all())
        self.assertEqual(game.players.count(), 1)

        self.mock_push_player_quit_game_event.assert_not_called()
        self.mock_update_lobby_list_player_count.assert_not_called()
        self.mock_update_lobby_list_remove_game.assert_not_called()
        self.mock_update_lobby_list_add_connect_quatro.assert_not_called()

        calls = self.mock_alert_game_players_to_new_move.call_args_list
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0][0], game)

        passed_game_state = calls[0][0][1]
        self.assertTrue(passed_game_state['game_over'])
        self.assertEqual(
            passed_game_state['winner'],
            {'slug':self.player2.slug, 'handle':self.player2.handle})

        self.assertIsNotNone(game.completedgame)
        self.assertEqual(game.completedgame.winners.count(), 1)
        self.assertEqual(game.completedgame.winners.first(), self.player2)
