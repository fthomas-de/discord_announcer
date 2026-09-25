"""App Settings"""

# Django
from django.conf import settings

# interval in hours preset for a new configuration row
TIME_DELTA = getattr(settings, "TIME_DELTA", 12)
