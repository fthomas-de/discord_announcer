"""What a post says: amounts, grouping and the source line."""

from discord_announcer.utilities import describe_source, format_sales, millify

from .base import (
    OTHER_STATION_ID,
    OTHER_STATION_NAME,
    PYERITE,
    STATION_ID,
    STATION_NAME,
    TRITANIUM,
    DiscordAnnouncerTestCase,
    make_config,
    make_corporation,
    make_division,
    make_names,
    make_sale,
)


class TestMillify(DiscordAnnouncerTestCase):
    def test_should_keep_two_decimals_in_the_unit(self):
        """Whole units cut 1.49 billion to "1 Billion", a third less than sold."""
        self.assertEqual(millify(1_490_000_000), "1.49 Billion")

    def test_should_pick_the_unit_after_rounding(self):
        """Picked first, 999,999 became "1000 Thousand"."""
        self.assertEqual(millify(999_999), "1.00 Million")
        self.assertEqual(millify(999_600), "999.60 Thousand")

    def test_should_leave_small_amounts_in_isk(self):
        self.assertEqual(millify(950), "950.00")
        self.assertEqual(millify(0), "0.00")

    def test_should_stop_at_the_largest_unit(self):
        self.assertEqual(millify(5_000_000_000_000_000), "5000.00 Trillion")


class TestFormatSales(DiscordAnnouncerTestCase):
    def setUp(self):
        make_names()

    def test_should_sum_quantity_and_value_per_station_and_type(self):
        sales = [
            make_sale(quantity=10, unit_price=5.0),
            make_sale(quantity=5, unit_price=4.0),
            make_sale(type_id=PYERITE, quantity=2, unit_price=1_000_000.0),
        ]

        station, text = format_sales(sales)[0]

        self.assertEqual(station, STATION_NAME)
        self.assertEqual(
            text.splitlines(),
            ["Pyerite x 2 for 2.00 Million ISK", "Tritanium x 15 for 70.00 ISK"],
        )

    def test_should_give_every_station_its_own_entry_ordered_by_name(self):
        """By name rather than by location id, so Amarr comes before Jita."""
        sales = [make_sale(location_id=STATION_ID), make_sale(location_id=OTHER_STATION_ID)]

        self.assertEqual(
            [station for station, _ in format_sales(sales)], [OTHER_STATION_NAME, STATION_NAME]
        )

    def test_should_name_an_unknown_station_and_type_by_their_id(self):
        """Left out, those sales were lost for good: the window moved on
        past them all the same."""
        sales = [make_sale(location_id=1_234_567_890_123, type_id=99_999)]

        station, text = format_sales(sales)[0]

        self.assertEqual(station, "Location 1234567890123")
        self.assertTrue(text.startswith("Type 99999 x 10 for"))

    def test_should_write_isk_the_way_eve_does(self):
        text = format_sales([make_sale(type_id=TRITANIUM)])[0][1]

        self.assertTrue(text.endswith(" ISK"))


class TestDescribeSource(DiscordAnnouncerTestCase):
    def test_should_name_the_corporation_and_the_division_with_its_game_name(self):
        corporation = make_corporation()
        make_division(corporation, division=5, name="Verkauf")
        config = make_config(corporation=corporation, division=5)

        author, logo = describe_source(config)

        self.assertEqual(author, "Bravo Corp [BRAVO] · Wallet division 5 (Verkauf)")
        self.assertEqual(logo, corporation.logo_url_64)

    def test_should_fall_back_to_the_number_without_a_name(self):
        config = make_config(division=3)

        self.assertTrue(describe_source(config)[0].endswith("· Wallet division 3"))
