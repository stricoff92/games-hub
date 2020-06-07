
from django.conf import settings

def is_testing():
    return hasattr(settings, "IS_TESTING") and settings.IS_TESTING
