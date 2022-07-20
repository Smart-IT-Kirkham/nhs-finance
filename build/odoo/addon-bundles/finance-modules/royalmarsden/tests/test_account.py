import logging
from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests.common import Form, SavepointCase

from ..helpers import redirect_setupclass_exception


class AccountCommon(SavepointCase):
    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(AccountCommon, cls).setUpClass()
        cls.payment_method_manual = cls.env["account.payment.method"].search(
            [("payment_type", "=", "outbound"), ("code", "=", "manual")], limit=1
        )
        cls.bank_journal = cls.env["account.journal"].search(
            [("type", "=", "bank")], limit=1
        )
        cls.purchase_journal = cls.env["account.journal"].search(
            [("type", "=", "purchase")], limit=1
        )
        cls.vendor_partner = cls.env.ref("base.res_partner_2")
        cls.vendor_partner_multi_banks = cls.env.ref("base.res_partner_3")
        cls.vendor_partner_none_banks = cls.env.ref("base.res_partner_12")
        cls.logger = logging.getLogger(__name__)

    @classmethod
    def register_payment(
        cls, move, payment_amount, payment_type, communication, partner
    ):
        payment_form = Form(
            cls.env["account.payment"].with_context(
                active_id=move.id, active_ids=move.ids, active_model="account.move"
            )
        )
        payment_form.payment_type = payment_type
        payment_form.journal_id = cls.bank_journal
        payment_form.payment_date = date.today()
        payment_form.partner_type = "supplier"
        payment_form.partner_id = partner
        payment_form.amount = payment_amount
        payment_form.communication = communication
        cls.payment_form = payment_form.save()
        cls.payment_form.post()


class AccountBase(AccountCommon):
    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(AccountBase, cls).setUpClass()
        cls.purchasable_product_a = cls.env.ref(
            "product.product_product_4d"
        )  # Demo data
        # Could not get these to work with formemulator.
        cls.vendor_bill_a = cls.env["account.move"].create(
            dict(
                type="in_invoice",
                date=date.today(),
                journal_id=cls.env["account.journal"]
                .search([("type", "=", "purchase")], limit=1)
                .id,
                partner_id=cls.vendor_partner.id,
            )
        )
        cls.vendor_bill_a_line_a = (
            cls.env["account.move.line"]
            .with_context(check_move_validity=False)
            .create(
                dict(
                    move_id=cls.vendor_bill_a.id,
                    product_id=cls.purchasable_product_a.id,
                    account_id=cls.env["account.account"]
                    .search([("code", "=", 500000)])
                    .id,
                    quantity=2,
                    price_unit=50,
                    debit=100.0,
                    credit=0.0,
                )
            )
        )
        cls.expected_posted_date = False
        cls.expected_payment_amount = 0
        cls.expected_amount_total = 100
        cls.expected_amount_residual = 0
        cls.expected_payment_numbers_concat = ""
        cls.expected_payment_journals_concat = ""
        cls.vendor_bill_multi_bank_accounts = cls.env["account.move"].create(
            dict(
                type="in_invoice",
                date=date.today(),
                journal_id=cls.env["account.journal"]
                .search([("type", "=", "purchase")], limit=1)
                .id,
                partner_id=cls.vendor_partner_multi_banks.id,
            )
        )
        cls.vendor_bill_multi_line_a = (
            cls.env["account.move.line"]
            .with_context(check_move_validity=False)
            .create(
                dict(
                    move_id=cls.vendor_bill_multi_bank_accounts.id,
                    product_id=cls.purchasable_product_a.id,
                    account_id=cls.env["account.account"]
                    .search([("code", "=", 500000)])
                    .id,
                    quantity=2,
                    price_unit=50,
                    debit=100.0,
                    credit=0.0,
                )
            )
        )
        cls.vendor_bill_multi_bank_accounts.post()
        cls.vendor_bill_none_bank_accounts = cls.env["account.move"].create(
            dict(
                type="in_invoice",
                date=date.today(),
                journal_id=cls.env["account.journal"]
                .search([("type", "=", "purchase")], limit=1)
                .id,
                partner_id=cls.vendor_partner_none_banks.id,
            )
        )
        cls.vendor_bill_none_line_a = (
            cls.env["account.move.line"]
            .with_context(check_move_validity=False)
            .create(
                dict(
                    move_id=cls.vendor_bill_none_bank_accounts.id,
                    product_id=cls.purchasable_product_a.id,
                    account_id=cls.env["account.account"]
                    .search([("code", "=", 500000)])
                    .id,
                    quantity=2,
                    price_unit=50,
                    debit=100.0,
                    credit=0.0,
                )
            )
        )
        cls.vendor_bill_none_bank_accounts.post()

    def test_posted_date(self):
        self.assertEqual(self.vendor_bill_a.posted_date, self.expected_posted_date)

    def test_amounts(self):
        self.assertEqual(self.vendor_bill_a.amount_total, self.expected_amount_total)
        self.assertEqual(
            self.vendor_bill_a.amount_residual, self.expected_amount_residual
        )
        self.assertEqual(
            self.vendor_bill_a.payment_amount_sum,
            self.expected_payment_amount,
            "Expected payment_amount_sum to be the sum of all payment lines",
        )

    def test_payment_strings(self):
        self.assertEqual(
            self.vendor_bill_a.payment_numbers_concat,
            self.expected_payment_numbers_concat,
        )
        self.assertEqual(
            self.vendor_bill_a.payment_journals_concat,
            self.expected_payment_journals_concat,
        )

    def test_journal_with_currency_display(self):
        self.assertEqual(
            self.vendor_bill_a.journal_with_currency_display, "Vendor Bills (GBP)"
        )


class TestAccountMovePostActions(AccountBase):
    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(TestAccountMovePostActions, cls).setUpClass()
        cls.vendor_bill_a.action_post()
        cls.expected_posted_date = date.today()
        cls.expected_payment_amount = 0
        cls.expected_amount_total = 100
        cls.expected_amount_residual = 100


class TestAccountMoveDuplicateActions(TestAccountMovePostActions):
    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(TestAccountMoveDuplicateActions, cls).setUpClass()
        cls.vendor_bill_a = cls.vendor_bill_a.copy()
        cls.expected_posted_date = False


class TestAccountMoveCancelActions(TestAccountMovePostActions):
    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(TestAccountMoveCancelActions, cls).setUpClass()
        cls.vendor_bill_a.button_cancel()
        cls.expected_posted_date = False


class TestAccountMovePayAction(TestAccountMovePostActions):
    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(TestAccountMovePayAction, cls).setUpClass()
        cls.register_payment(
            cls.vendor_bill_a, 50, "outbound", "TESTPAY1", cls.vendor_partner
        )
        cls.expected_payment_amount = 50
        cls.expected_amount_total = 100
        cls.expected_amount_residual = 50
        # It's tricky to get the journal name of the payment, so i'm just assuming
        # (which it does on a clean test db) that it is the first journal of its type
        year = date.today().year
        cls.expected_payment_numbers_concat = "BNK1/{}/0001 (TESTPAY1)".format(year)
        cls.expected_payment_journals_concat = "Bank"

    def test_dont_allow_payment_post_multi_bank_accounts(self):
        with self.assertRaises(ValidationError) as cm:
            self.register_payment(
                self.vendor_bill_multi_bank_accounts,
                50,
                "outbound",
                "TESTPAY1",
                self.vendor_partner_multi_banks,
            )
        self.logger.debug(cm.exception)

    def test_dont_allow_payment_post_none_bank_accounts(self):
        with self.assertRaises(ValidationError) as cm:
            self.register_payment(
                self.vendor_bill_none_bank_accounts,
                50,
                "outbound",
                "TESTPAY1",
                self.vendor_partner_none_banks,
            )
        self.logger.debug(cm.exception)


class TestAccountMovePayAgainAction(TestAccountMovePayAction):
    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(TestAccountMovePayAgainAction, cls).setUpClass()
        cls.register_payment(
            cls.vendor_bill_a, 25, "outbound", "TESTPAY2", cls.vendor_partner
        )
        cls.expected_payment_amount = 75
        cls.expected_amount_total = 100
        cls.expected_amount_residual = 25
        year = date.today().year
        cls.expected_payment_numbers_concat = (
            "BNK1/{}/0001 (TESTPAY1), BNK1/{}/0002 (TESTPAY2)".format(year, year)
        )
        cls.expected_payment_journals_concat = "Bank, Bank"


# DEBT: Missing test coverage of odoo csv export functionality
