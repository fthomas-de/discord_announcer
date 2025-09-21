from allianceauth.services.hooks import get_extension_logger

from discord_announcer.app_settings import REQUIRED_SCOPE

from allianceauth.eveonline.models import EveCharacter
from esi.models import Token

from .provider import esi

logger = get_extension_logger(__name__)


def get_chars_in_corp(corp_id: int):
    chars_in_corp = EveCharacter.objects.filter(corporation_id=corp_id).all().values_list("character_id", flat=True).all()
    if not chars_in_corp:
        logger.error("No characters found in corporation: %s", corp_id)
        return None
    return chars_in_corp


def get_corp_transaction_token(corp_id: int) -> Token:
    if corp_id is None:
        logger.error("Corporation ID is None")
        return False
    
    chars_in_corp = get_chars_in_corp(corp_id)
    token = Token.objects.filter(scopes__name=REQUIRED_SCOPE, character_id__in=chars_in_corp).first()

    if not token:
        logger.error("No token found with required scope: %s", REQUIRED_SCOPE)
        return False
    return token


def get_transactions(corp_id: int, division: int):
    token = get_corp_transaction_token(corp_id)
    transactions = esi.client.Wallet.get_corporations_corporation_id_wallets_division_transactions(corporation_id=corp_id, division=division, token=token.valid_access_token()).result()

    if not transactions:
        logger.info("No transactions found for corporation: %s", corp_id)
        return None
    
    return transactions


def get_transactions_for_timeframe(time: int, corporation_id: int, division: int):
    transactions = get_transactions(corporation_id, division)
    if transactions is None:
        logger.info("No transactions found")
        return []

    sales = [t for t in transactions if t['date'] >= time and t['is_buy'] is False]

    return sales