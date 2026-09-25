"""Reading the wallet: which token, which transactions, which sales."""

from datetime import timedelta
from types import SimpleNamespace
from unittest import mock

from discord_announcer import selects
from discord_announcer.selects import (
    WALLET_ROLES,
    WALLET_SCOPE,
    get_corp_transaction_token,
    get_latest_sale,
    get_sales_since,
    get_transactions,
)

from .base import CORP_ID, NOW, DiscordAnnouncerTestCase, make_sale

TOKEN = SimpleNamespace(character_name="Accountant Alt")


class TestTokenChoice(DiscordAnnouncerTestCase):
    def test_should_ask_corptools_for_a_token_with_one_of_the_wallet_roles(self):
        """The first token with the scope failed every run as soon as its
        character lacked the role, although another member would have worked;
        corptools tries them in turn and checks the role."""
        with mock.patch.object(selects, "get_corp_token", return_value=TOKEN) as helper:
            self.assertIs(get_corp_transaction_token(CORP_ID), TOKEN)

        helper.assert_called_once_with(CORP_ID, [WALLET_SCOPE], WALLET_ROLES)
        self.assertIn("Director", WALLET_ROLES)

    def test_should_hand_corptools_a_fresh_scope_list_each_time(self):
        """get_corp_token appends the roles scope to the list it is given."""
        seen = []

        def helper(corp_id, scopes, roles):
            seen.append(scopes)
            scopes.append("esi-characters.read_corporation_roles.v1")

        with mock.patch.object(selects, "get_corp_token", side_effect=helper):
            get_corp_transaction_token(CORP_ID)
            get_corp_transaction_token(CORP_ID)

        self.assertEqual(seen[1], [WALLET_SCOPE, "esi-characters.read_corporation_roles.v1"])
        self.assertIsNot(seen[0], seen[1])


class TestGetTransactions(DiscordAnnouncerTestCase):
    def setUp(self):
        patch = mock.patch.object(selects, "esi")
        self.esi = patch.start()
        self.addCleanup(patch.stop)
        self.operation = self.esi.client.Wallet.GetCorporationsCorporationIdWalletsDivisionTransactions

    def test_should_refuse_without_a_token(self):
        """Raised rather than an empty list, so the window stays open."""
        with mock.patch.object(selects, "get_corp_transaction_token", return_value=None):
            with self.assertRaises(ValueError):
                get_transactions(CORP_ID, 1)

    def test_should_skip_the_etag_and_pass_the_cache_choice_on(self):
        """django-esi 9 raises HTTPNotModified on unchanged data otherwise."""
        get_transactions(CORP_ID, 1, token=TOKEN, use_cache=False)

        self.operation.return_value.results.assert_called_once_with(use_etag=False, use_cache=False)

    def test_should_ask_for_older_pages_by_from_id(self):
        get_transactions(CORP_ID, 1, token=TOKEN, from_id=42)

        self.assertEqual(self.operation.call_args.kwargs["from_id"], 42)

    def test_should_leave_from_id_out_for_the_newest_page(self):
        get_transactions(CORP_ID, 1, token=TOKEN)

        self.assertNotIn("from_id", self.operation.call_args.kwargs)


class TestSales(DiscordAnnouncerTestCase):
    def test_should_keep_sales_after_the_window_start_only(self):
        inside = make_sale(minutes_ago=30)
        at_start = make_sale(minutes_ago=60)
        bought = make_sale(minutes_ago=10, is_buy=True)

        with mock.patch.object(selects, "get_transactions", return_value=[inside, at_start, bought]):
            sales, newest = get_sales_since(NOW - timedelta(hours=1), CORP_ID, 1)

        # the window start itself belongs to the previous window
        self.assertEqual(sales, [inside])
        self.assertEqual(newest, bought.transaction_id)

    def test_should_report_no_newest_id_for_an_empty_answer(self):
        with mock.patch.object(selects, "get_transactions", return_value=[]):
            self.assertEqual(get_sales_since(NOW, CORP_ID, 1), ([], None))

    def test_should_find_the_newest_sale_and_ignore_purchases(self):
        old = make_sale(minutes_ago=300)
        new = make_sale(minutes_ago=5)
        bought = make_sale(minutes_ago=1, is_buy=True)

        with mock.patch.object(selects, "get_transactions", return_value=[old, bought, new]):
            self.assertIs(get_latest_sale(CORP_ID, 1, token=TOKEN), new)

    def test_should_find_no_latest_sale_without_sales(self):
        with mock.patch.object(selects, "get_transactions", return_value=[make_sale(is_buy=True)]):
            self.assertIsNone(get_latest_sale(CORP_ID, 1, token=TOKEN))
