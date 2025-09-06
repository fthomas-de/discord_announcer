"""App Settings"""

# Django
from django.conf import settings

# put your app settings here

DIVISION = getattr(settings, "DIVISION", 2)
REV_TYPE = getattr(settings, "REV_TYPE", ['market_transaction'])
