from datetime import datetime

from allianceauth.services.hooks import get_extension_logger

from allianceauth.eveonline.models import EveCorporationInfo
from corptools.models import CorporationWalletDivision
from corptools.tasks.corporation.utils import get_corp_token
from esi.models import Token

from .provider import esi

logger = get_extension_logger(__name__)

# The one scope the wallet transactions need. Not a setting: ESI decides it,
# and any other value only ever made every row fail.
WALLET_SCOPE = "esi-wallet.read_corporation_wallets.v1"

# The in-game roles ESI accepts for a corporation wallet - the list corptools
# itself asks for in tasks/corporation/wallet.py. get_corp_token checks them
# through the roles scope, which it adds to the wallet scope on its own.
WALLET_ROLES = ["CEO", "Director", "Accountant", "Junior_Accountant"]

# ESI returns the newest 2500 transactions per page. When a window reaches
# further back than one page, older pages are asked for with from_id - but
# only this many, so one wallet cannot keep a run busy without end.
MAX_PAGES = 5


def get_corp_transaction_token(corp_id: int) -> Token | None:
    """A token of the corporation that may read its wallet, or None.

    corptools' own helper: it tries the tokens with the scopes one after the
    other and returns the first whose character holds one of the roles. Taking
    the first token with the scope alone failed every run as soon as that
    character lacked the role, although another member would have worked.
    """
    # a fresh list: get_corp_token appends the roles scope to the one it gets
    return get_corp_token(corp_id, [WALLET_SCOPE], WALLET_ROLES)


def get_transactions(corp_id: int, division: int, token: Token | None = None,
                     use_cache: bool = True, from_id: int | None = None) -> list:
    token = token or get_corp_transaction_token(corp_id)
    if not token:
        # Raised rather than returning nothing, so the caller keeps the window
        # open instead of treating it as a window without sales.
        raise ValueError(
            f"No token with scope {WALLET_SCOPE} and one of the roles "
            f"{', '.join(WALLET_ROLES)} for corporation {corp_id}"
        )

    extra = {"from_id": from_id} if from_id is not None else {}

    # The ETag check raises HTTPNotModified on unchanged data; we always want the list.
    return esi.client.Wallet.GetCorporationsCorporationIdWalletsDivisionTransactions(
        corporation_id=corp_id, division=division, token=token, **extra
    ).results(use_etag=False, use_cache=use_cache)


def get_transactions_after(corp_id: int, division: int, last_id: int) -> list:
    """Every transaction newer than last_id, older pages fetched as needed."""
    token = get_corp_transaction_token(corp_id)
    found = []
    from_id = None

    for _ in range(MAX_PAGES):
        page = get_transactions(corp_id, division, token=token, from_id=from_id)
        found.extend(t for t in page if t.transaction_id > last_id)

        oldest = min((t.transaction_id for t in page), default=None)

        # the page reached back to what was seen already, or there is nothing older
        if oldest is None or oldest <= last_id:
            return found

        from_id = oldest - 1
    else:
        logger.warning(
            f"[discord_announcer] More than {MAX_PAGES} pages of transactions since "
            f"transaction {last_id} for corporation {corp_id}, division {division}; "
            f"the older ones are left out"
        )

    return found


def get_division_name(corporation: EveCorporationInfo, division: int) -> str | None:
    """Name the corporation gave the wallet division in game, as synced by Corp Tools."""
    return (
        CorporationWalletDivision.objects.filter(corporation__corporation=corporation, division=division)
        .values_list("name", flat=True)
        .first()
    )


def get_latest_sale(corp_id: int, division: int, token: Token | None = None):
    """The newest sale ESI still returns for the division, or None."""
    sales = [t for t in get_transactions(corp_id, division, token=token) if not t.is_buy]

    return max(sales, key=lambda sale: sale.date, default=None)


def get_sales_since(since: datetime, corporation_id: int, division: int) -> tuple[list, int | None]:
    """Sales after `since`, for a row that has no transaction to start after yet.

    Returns the sales and the newest transaction id the answer held, sold or
    bought, which is where the next window starts.
    """
    transactions = get_transactions(corporation_id, division)
    newest = max((t.transaction_id for t in transactions), default=None)

    return [t for t in transactions if t.date > since and not t.is_buy], newest
