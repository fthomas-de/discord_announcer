"""App Settings"""

# Django
from django.conf import settings

# put your app settings here

DIVISION = getattr(settings, "DIVISION", 5)
CORPORATION_ID = getattr(settings, "CORPORATION_ID", 98633815)
REF_TYPE = getattr(settings, "REF_TYPE", ['market_transaction'])
TIME_DELTA = getattr(settings, "TIME_DELTA", 12)
REQUIRED_SCOPE = getattr(settings, "REQUIRED_SCOPE", "esi-wallet.read_corporation_wallets.v1")
CHANNEL_ID = getattr(settings, "CHANNEL_ID", 1413885436366950582)