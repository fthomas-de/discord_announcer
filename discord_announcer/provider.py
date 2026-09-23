from esi.openapi_clients import ESIClientProvider

from discord_announcer import __compat_date__, __title__, __url__, __version__


class DA_Provider(ESIClientProvider):
    pass

esi = DA_Provider(
    compatibility_date=__compat_date__,
    ua_appname=__title__,
    ua_version=__version__,
    ua_url=__url__,
    operations=[
        "GetCorporationsCorporationIdWalletsDivisionTransactions",
    ],
)
