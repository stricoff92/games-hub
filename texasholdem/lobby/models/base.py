
from django.db import models


class AbstractBaseModel(models.Model):
    """Base model for other models to inherit
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

