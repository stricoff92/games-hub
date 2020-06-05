
import random
from uuid import uuid4

from django.db import transaction
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from lobby.models.game import Game
from lobby.models.player import Player



def _true_or_false(probability_true=0.5):
    x = random.randint(1, 100)
    return (probability_true * 100) > x

def full_name_to_user_name(full_name):
    chars = "".join(full_name).replace(" ", "")
    if _true_or_false():
        return chars[0] + chars[-5:]
    else:
        return chars[:3] + chars[7:]





class Command(BaseCommand):

    help = ''

    def get_batch_id(self):
        return uuid4().hex[:8]
    
    @transaction.atomic
    def handle(self, *args, **options):
        FAKE_NAMES = ("Conrad Durham","Shanna Wooten","Roach Espinoza", "Wolfe Cain","Bruce Madden","Glenda Burch","Violet Rodriquez","Flynn Contreras","Rutledge Hart","Cornelia Flynn","Wise Hoffman","Kellie Snow","Guy Michael","Juliet Best","Alma Morin","Mollie Pollard","Josefa David","Joan Whitley","Becker Melton","Marshall Cochran","Mccray Harris","Santana Webb","Sharon Noble","Desiree Byers","Miranda Rosa","Brooke Baird","Macias Cleveland","Olsen Lloyd","Mays Mcgee","Collins Shields","Leach Caldwell","Latisha Barton","Grant Watts","Kerri Burt","Millicent Curry","Pope Bradford","Jeanne Weaver","Ladonna Marshall","Newman Lynch","Jacobson Nelson","Haney Munoz","Lawanda Banks","Alicia Norton","Danielle Tran","Linda Workman","Staci Herman","Brady Watkins","Hamilton Sampson","Hood Avila","Nannie Strickland","Tucker Fisher","Swanson Torres","Hess Griffith","Dillon Parker","Phelps Osborne","Fowler Lambert","Dorsey Tanner","Jenna Holland","Jaclyn Webster","Walters Keller","Willa Delaney","Vicky Delgado","Carson Greer","Liliana Cannon","Lynette Clements","Rogers Dotson","Walton Hughes","Tran Bender","Lee Mcneil","Mona Mccarthy","Regina Whitaker","Small Page","Tessa Abbott","Lena Gomez","Malinda Walter","Lori Chapman","Lenore Ashley","Sargent Ramos","Tammi Cabrera","Becky Drake","Bridgette Elliott","Harrington Rice","Celeste Houston","Melisa Wong","Le Prince","Josefina Nixon","Elnora Mayo","Luna Hubbard","Mckinney Moody","Hendricks Gibson","Angela Sanders","Chang Obrien","Cardenas Booth","Mcconnell Frost","Betty Hendricks","Barbra Key","Pearl Chaney","Bryant Flores","Magdalena Peterson","Wade Combs",)
        FAKE_USER_NAMES = tuple(
            full_name_to_user_name(full_name) for full_name in FAKE_NAMES
        )


        user_count = 100
        batch_id = self.get_batch_id()

        randomly_sorted_user_names = sorted(
            FAKE_USER_NAMES, key=lambda v: random.randint(1, 100))

        for username in randomly_sorted_user_names:
            username = batch_id + '-' + username
            email = f"{batch_id}-{username}@mail.com"
            password = f"pass{username}"
            user = User.objects.create_user(username, email, password)
            player = Player.objects.create(user=user, handle=username)
            print("user/player", username, "created")
