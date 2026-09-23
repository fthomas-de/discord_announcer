from datetime import datetime

from allianceauth.services.hooks import get_extension_logger

from discord_announcer.app_settings import REQUIRED_SCOPE

from allianceauth.eveonline.models import EveCharacter
from esi.models import Token

from .provider import esi

logger = get_extension_logger(__name__)


def get_chars_in_corp(corp_id: int):
    chars_in_corp = EveCharacter.objects.filter(corporation_id=corp_id).values_list("character_id", flat=True)
    if not chars_in_corp:
        logger.error("[discord_announcer] No characters found in corporation: %s", corp_id)
        return None
    return chars_in_corp


def get_corp_transaction_token(corp_id: int) -> Token | None:
    chars_in_corp = get_chars_in_corp(corp_id)
    if not chars_in_corp:
        return None

    return Token.objects.filter(scopes__name=REQUIRED_SCOPE, character_id__in=chars_in_corp).first()


def get_transactions(corp_id: int, division: int) -> list:
    token = get_corp_transaction_token(corp_id)
    if not token:
        # Raised rather than returning nothing, so the caller keeps the window
        # open instead of treating it as a window without sales.
        raise ValueError(f"No token with scope {REQUIRED_SCOPE} for corporation {corp_id}")

    # The ETag check raises HTTPNotModified on unchanged data; we always want the list.
    return esi.client.Wallet.GetCorporationsCorporationIdWalletsDivisionTransactions(
        corporation_id=corp_id, division=division, token=token
    ).results(use_etag=False)


def get_sales_since(since: datetime, corporation_id: int, division: int) -> list:
    """Sales in the window after `since`, up to now."""
    transactions = get_transactions(corporation_id, division)

    return [t for t in transactions if t.date > since and not t.is_buy]
