
from django import forms

from lobby.models import Game, Player

# TODO: DELETE
class NewGameForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = ['game_type', 'name']


class LoginForm(forms.Form):
    username = forms.CharField(label='Username')
    password = forms.CharField(widget=forms.PasswordInput)

class RegistrationForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField()
    handle = forms.CharField()


class GameTypeSelectionForm(forms.Form):
    roomtype = forms.CharField(required=True)

    def clean(self):
        cleaned_data = super().clean()
        roomtype = cleaned_data['roomtype']
        available_types = [c[0] for c in Game.GAME_TYPE_CHOICES]
        if roomtype not in available_types:
            raise forms.ValidationError("invalid roomtype")
        return cleaned_data

class NewConnectQuatroRoomForm(forms.Form):
    roomname = forms.CharField(required=True)
    boarddimx = forms.IntegerField(required=True)
    boarddimy = forms.IntegerField(required=True)
    boardplayercount = forms.IntegerField(required=True)
    boardwincount = forms.IntegerField(required=True)

    def clean(self):
        cleaned_data = super().clean()
        if 5 > cleaned_data['boarddimx'] > 20:
            raise forms.ValidationError(
                "boarddimx must be between 5 and 20")
        if 5 > cleaned_data['boarddimy'] > 20:
            raise forms.ValidationError(
                "boarddimy must be between 5 and 20")

        if 3 > cleaned_data['boardwincount'] > 15:
            raise forms.ValidationError(
                "boardwincount must be between 3 and 13")
        
        if max(cleaned_data['boarddimx'], cleaned_data['boarddimy']) < cleaned_data['boardwincount']:
            raise forms.ValidationError(
                "Board too small for boardwincount")
        
        if cleaned_data['boardplayercount'] > len(Player.COLOR_CHOICES):
            raise forms.ValidationError("boardplayercount too large")

        if cleaned_data['boardplayercount'] < 2:
            raise forms.ValidationError("boardplayercount too small")
        
        return cleaned_data
