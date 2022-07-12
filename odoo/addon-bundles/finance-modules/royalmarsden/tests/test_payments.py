from contextlib import suppress

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import Form, TransactionCase


class GroupedPayments(TransactionCase):
    def setUp(self):
        super().setUp()
        self.payment_method_manual = self.env["account.payment.method"].search(
            [("payment_type", "=", "outbound"), ("code", "=", "manual")],
            limit=1,
        )
        self.vendor_deco_addict = self.env.ref("base.res_partner_2")
        self.vendor_deco_addict_2 = self.vendor_deco_addict.copy(
            dict(
                name="Deco Addict 2",
            )
        )
        self.customizable_desk = self.env.ref("product.product_product_4d")

    def all_payments_now(self):
        return self.env["account.payment"].search([])

    def new_vendor_bill_form(self):
        return Form(self.env["account.move"].with_context(default_type="in_invoice"))

    def new_vendor_refund_form(self):
        return Form(self.env["account.move"].with_context(default_type="in_refund"))

    def post_new_bill_or_refund(self, *, amount, form, partner):
        form.partner_id = partner
        form.invoice_partner_bank_id = null(self.env["res.partner.bank"])
        with form.invoice_line_ids.new() as line:
            line.product_id = self.customizable_desk
            line.price_unit = amount
        bill_or_refund = form.save()
        bill_or_refund.action_post()
        return bill_or_refund

    def prepare_grouped_payment(self, *, moves):
        form = Form(
            self.env["account.payment.register"].with_context(
                active_ids=moves.ids,
                active_model="account.move",
            )
        )
        form.group_payment = True
        form.payment_date = fields.Date.today()
        form.payment_method_id = self.payment_method_manual
        return form.save()


class TestGroupedNegativeVendorPayments(GroupedPayments):
    def setUp(self):
        super().setUp()
        self.vendor_bill = self.post_new_bill_or_refund(
            amount=50,
            form=self.new_vendor_bill_form(),
            partner=self.vendor_deco_addict,
        )
        self.vendor_refund = self.post_new_bill_or_refund(
            amount=100,
            form=self.new_vendor_refund_form(),
            partner=self.vendor_deco_addict_2,
        )

    def test_registering_negative_grouped_payment_does_not_create_payments(self):
        payments_before = self.all_payments_now()
        self.env.user.company_id.combined_payment = True
        wizard = self.prepare_grouped_payment(
            moves=(self.vendor_bill + self.vendor_refund)
        )
        with suppress(ValidationError):
            wizard.create_payments()
        new_payments = self.all_payments_now() - payments_before
        self.assertEqual(new_payments, self.env["account.payment"], "empty set")

    def test_registering_negative_grouped_payment_throws_ValidationError(self):
        self.env.user.company_id.combined_payment = True
        wizard = self.prepare_grouped_payment(
            moves=(self.vendor_bill + self.vendor_refund)
        )
        with self.assertRaises(ValidationError):
            wizard.create_payments()


class TestGroupedPositiveVendorPayments(GroupedPayments):
    def test_registering_positive_vendor_payments_results_in_new_payments(self):
        vendor_bill = self.post_new_bill_or_refund(
            amount=100,
            form=self.new_vendor_bill_form(),
            partner=self.vendor_deco_addict,
        )
        vendor_refund = self.post_new_bill_or_refund(
            amount=50,
            form=self.new_vendor_refund_form(),
            partner=self.vendor_deco_addict,
        )
        payments_before = self.all_payments_now()
        self.env.user.company_id.combined_payment = True
        wizard = self.prepare_grouped_payment(moves=(vendor_bill + vendor_refund))
        wizard.create_payments()
        new_payments = self.all_payments_now() - payments_before
        self.assertTrue(new_payments, "have new payments")


class TestGroupedCustomerPaymentsForRefundLargerThanBill(GroupedPayments):
    def setUp(self):
        super().setUp()
        customer_form = self.new_customer_form()
        customer_form.name = "Yetta Feldman"
        with customer_form.bank_ids.new() as bank:
            bank.bank_id = self.env["res.bank"].search([("name", "=", "Reserve")])
            bank.acc_number = "21122112"
            bank.sort_code = "42-42-42"
        self.customer = customer_form.save()

    def test_is_allowed_and_results_in_an_single_inbound_payment_for_the_difference(
        self,
    ):
        self.env.user.company_id.combined_payment = True
        customer_invoice = self.post_new_bill_or_refund(
            amount=500,
            form=self.new_customer_invoice_form(),
            partner=self.customer,
        )
        customer_refund = self.post_new_bill_or_refund(
            amount=200,
            form=self.new_customer_refund_form(),
            partner=self.customer,
        )
        payments_before = self.all_payments_now()

        wizard = self.prepare_grouped_payment(
            moves=(customer_invoice + customer_refund)
        )
        wizard.create_payments()

        new_payments = self.all_payments_now() - payments_before
        self.assertEqual(len(new_payments), 1, "one new payment")
        self.assertEqual(
            new_payments[0].payment_type, "inbound", "payment type is inbound"
        )
        self.assertEqual(
            new_payments[0].amount,
            300,
            "amount is 300 (the difference between invoice and refund)",
        )

    def new_customer_form(self):
        return Form(self.env["res.partner"])

    def new_customer_invoice_form(self):
        return Form(self.env["account.move"].with_context(default_type="out_invoice"))

    def new_customer_refund_form(self):
        return Form(self.env["account.move"].with_context(default_type="out_refund"))


def null(model):
    return model.env[model._name]
