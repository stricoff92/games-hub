
from django import forms
from django.core.validators import (
    MinValueValidator,
)

class ConnectQuatroMoveForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self._max_column_index = kwargs.pop("max_column_index")
        return super().__init__(*args, **kwargs)

    column_index = forms.IntegerField(
        validators=[
            MinValueValidator(0, message="column_index must be greater than 0."),])
