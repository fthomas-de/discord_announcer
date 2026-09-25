from esi.openapi_clients import ESIClientProvider

from discord_announcer import __compat_date__, __title__, __url__, __version__

# The one ESI operation this app calls itself. The roles check behind the
# token choice runs through corptools' own provider.
esi = ESIClientProvider(
    compatibility_date=__compat_date__,
    ua_appname=__title__,
    ua_version=__version__,
    ua_url=__url__,
    operations=[
        "GetCorporationsCorporationIdWalletsDivisionTransactions",
    ],
)
