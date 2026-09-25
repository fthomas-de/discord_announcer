from collections import defaultdict

from corptools.models import EveItemType, EveLocation

from discord_announcer.selects import get_division_name

UNITS = ["", " Thousand", " Million", " Billion", " Trillion"]


def describe_source(config) -> tuple[str, str]:
    """Author line and logo naming the corporation and wallet division a post comes from."""
    corporation = config.corporation
    division = f"Wallet division {config.division}"
    division_name = get_division_name(corporation, config.division)

    if division_name:
        division += f" ({division_name})"

    return f"{corporation.corporation_name} [{corporation.corporation_ticker}] · {division}", corporation.logo_url_64


def millify(amount) -> str:
    """An ISK amount in the largest unit it reaches, to two decimals.

    The unit is chosen after rounding: picked first, 999,999 became
    "1000 Thousand". Whole units cut 1.49 billion to "1 Billion", a third
    less than was sold.
    """
    value = float(amount)
    index = 0

    while abs(value) >= 1000 and index < len(UNITS) - 1:
        value /= 1000
        index += 1

    value = round(value, 2)

    if abs(value) >= 1000 and index < len(UNITS) - 1:
        value = round(value / 1000, 2)
        index += 1

    return f"{value:.2f}{UNITS[index]}"


def format_sales(sales) -> list:
    """One (station, text) pair per station, stations and item types by name.

    A station or item type Corp Tools does not know yet is named by its id.
    Leaving those sales out lost them for good - the window moved on past
    them all the same.
    """
    location_ids = {sale.location_id for sale in sales}
    type_ids = {sale.type_id for sale in sales}

    locations = dict(
        EveLocation.objects.filter(location_id__in=location_ids).values_list("location_id", "location_name")
    )
    types = dict(EveItemType.objects.filter(type_id__in=type_ids).values_list("type_id", "name"))

    def location_name(location_id):
        return locations.get(location_id) or f"Location {location_id}"

    def type_name(type_id):
        return types.get(type_id) or f"Type {type_id}"

    per_station = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for sale in sales:
        total = per_station[sale.location_id][sale.type_id]
        total[0] += sale.quantity
        total[1] += sale.unit_price * sale.quantity

    formatted = []
    for location_id in sorted(per_station, key=location_name):
        lines = [
            f"{type_name(type_id)} x {quantity} for {millify(value)} ISK"
            for type_id, (quantity, value) in sorted(
                per_station[location_id].items(), key=lambda item: type_name(item[0])
            )
            if quantity > 0
        ]

        if lines:
            formatted.append((location_name(location_id), "\n".join(lines)))

    return formatted
