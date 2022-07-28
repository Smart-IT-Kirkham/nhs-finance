from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def post(self):
        res = super(AccountPayment, self).post()
        for payment in self:
            if not payment.partner_id.can_have_payment_posted():
                raise ValidationError(
                    _(
                        "You cannot confirm a payment, if the related partner "
                        "does not have only one bank account set up."
                    )
                )
            if payment.partner_type == "supplier":
                payment._send_remittance_advice_email()
        return res

    def _send_remittance_advice_email(self):
        template = self.env.ref("UK_Reports.email_template_remittance_advice_id")
        template.send_mail(self.id, force_send=True)

    @api.onchange("journal_id")
    def _onchange_journal(self):
        # If BACs payment method id is available to choose, automatically change to it
        res = super(AccountPayment, self)._onchange_journal()
        payment_method_id_domain = res.get("domain") and res.get("domain").get(
            "payment_method_id"
        )
        bacs_payment_method = self.env.ref(
            "royalmarsden.account_payment_method_bacs_out"
        )
        if payment_method_id_domain:
            if bacs_payment_method in self.env["account.payment.method"].search(
                payment_method_id_domain
            ):
                self.payment_method_id = bacs_payment_method
        return res


class AccountAccountHierarchy(models.Model):
    _name = "account.account.hierarchy"
    _description = "Chart of Accounts Hierarchy"

    name = fields.Char()
    level_1 = fields.Boolean(string="L1")
    level_2 = fields.Boolean(string="L2")
    level_3 = fields.Boolean(string="L3")
    level_4 = fields.Boolean(string="L4")
    level_5 = fields.Boolean(string="L5")


class AccountAccountCategory(models.Model):
    _name = "account.account.category"
    _description = "Chart of Accounts Category"

    name = fields.Char()


class AccountAccountParent(models.Model):
    _name = "account.account.parent"
    _description = "Chart of Accounts Parent"

    name = fields.Char()
    code = fields.Char()

    def name_get(self):
        res = []
        for account_parent in self:
            name = "[{}] {}".format(account_parent.code, account_parent.name)
            res.append((account_parent.id, name))
        return res


class AccountAccountGLGroup(models.Model):
    _name = "account.account.glgroup"
    _description = "Chart of Accounts GL Group"

    name = fields.Char()


class AccountAccount(models.Model):
    _inherit = "account.account"

    level_1_id = fields.Many2one(
        "account.account.hierarchy", domain=[("level_1", "=", True)]
    )
    level_2_id = fields.Many2one(
        "account.account.hierarchy", domain=[("level_2", "=", True)]
    )
    level_3_id = fields.Many2one(
        "account.account.hierarchy", domain=[("level_3", "=", True)]
    )
    level_4_id = fields.Many2one(
        "account.account.hierarchy", domain=[("level_4", "=", True)]
    )
    level_5_id = fields.Many2one(
        "account.account.hierarchy", domain=[("level_5", "=", True)]
    )
    category_id = fields.Many2one("account.account.category")
    # parent_id = fields.Many2one("account.account.parent")
    glgroup_id = fields.Many2one("account.account.glgroup", string="GL Group")


class AccountTax(models.Model):
    _inherit = "account.tax"

    jac_import_tax_name = fields.Char(
        string="JAC Import Oracle vat code name",
        help="""The name of the vat code as seen in the JAC Import file.
        Used to determine which Odoo tax to use on the vendor bill lines""",
    )


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    jac_import_payment_term_name = fields.Char(
        string="JAC Import payment term name",
        help="""The name of the payment term as seen in the JAC Import file.
        Used to determine which Odoo payment term to use on the vendor bill""",
    )


class AccountMove(models.Model):
    _inherit = "account.move"

    invoice_received_date = fields.Date(
        help="""Should be manually filled out.
        Signifies the date which the invoice was received from the supplier,
        either through post or email"""
    )
    # If the status of the invoice is changed to Cancelled or Draft for any reason,
    # then this will be set back to null.
    posted_date = fields.Date(
        readonly=True, help="Displays the date where the bill was posted", copy=False
    )
    purchase_invoice_description = fields.Char()
    url_input = fields.Char(string="URL")
    payment_numbers_concat = fields.Char(compute="_compute_payment_strings", store=True)
    payment_journals_concat = fields.Char(
        compute="_compute_payment_strings", store=True
    )
    payment_amount_sum = fields.Float(compute="_compute_payment_amount_sum", store=True)
    # When exporting journal, name_get doesn't appear to be used,
    # so we add a field which replicates name_get to include currency
    journal_with_currency_display = fields.Char(
        compute="_compute_journal_with_currency_display", store=True
    )
    created_from_purchase_id = fields.Many2one(
        "purchase.order",
        readonly=True,
        copy=False,
        help="Populated when a bill is created directly from a purchase order",
    )
    created_via_jac_import = fields.Boolean(
        help="""Set by the system during JAC Import.
                Not visible in the GUI"""
    )
    jac_import_token = fields.Char(
        help="""Set by the system during JAC Import. Is used to ensure we only look up
                invoices that are using the token for the current import.
                Not visible in the GUI"""
    )
    jac_prime_key = fields.Float(
        help="""Set by the system during JAC Import. Is used to link the invoice
                with its lines. Note that the prime key resets to 1 in each import file.
                Not visible in the GUI"""
    )
    jac_discount_amount = fields.Float(
        help="""Set by the system during JAC Import. Is used to store the discount
                amount with no effect until the lines are all added, then it will
                be pushed to `discount_amount`, and `discount_method` fields.
                Not visible in the GUI"""
    )

    @api.depends("journal_id")
    def _compute_journal_with_currency_display(self):
        for record in self:
            # this gives us [(<id>, <str>), ...]
            name_get_results = record.journal_id.name_get()
            for name_get_result in name_get_results:
                if name_get_result[0] == record.journal_id.id:
                    record.journal_with_currency_display = name_get_result[1]

    @api.depends("invoice_payments_widget")
    def _compute_payment_strings(self):
        for record in self:
            # invoice_payments_widget uses this to populate itself and then
            # gets transformed into a json.dumps(), so i'd rather not json.loads() it
            invoice_payments_widget_data = record._get_reconciled_info_JSON_values()
            if not invoice_payments_widget_data:
                record.payment_journals_concat = ""
                record.payment_numbers_concat = ""
            else:
                journals = [
                    x.get("journal_name")
                    for x in invoice_payments_widget_data
                    if x.get("journal_name")
                ]
                payment_numbers = [
                    x.get("ref") for x in invoice_payments_widget_data if x.get("ref")
                ]
                record.payment_journals_concat = ", ".join(journals)
                record.payment_numbers_concat = ", ".join(payment_numbers)

    @api.depends("amount_total", "amount_residual")
    def _compute_payment_amount_sum(self):
        for record in self:
            if record.state == "draft":
                record.payment_amount_sum = 0
            else:
                record.payment_amount_sum = record.amount_total - record.amount_residual

    def action_post(self):
        res = super(AccountMove, self).action_post()
        self.posted_date = fields.Date.today()
        return res

    def button_cancel(self):
        res = super(AccountMove, self).button_cancel()
        self.posted_date = False
        return res

    def post(self):
        # Preserve date if created via jac, as all moves created via jac are
        # auto-posted and without this we loose date information which was imported
        jac_original_moves_and_dates = {
            move: move.date
            for move in self.filtered(lambda x: x.created_via_jac_import is True)
        }
        res = super(AccountMove, self).post()
        for jac_move, original_date in jac_original_moves_and_dates.items():
            jac_move.date = original_date
        return res

    def action_invoice_register_payment(self):
        self.validate_bank_account_in_partners()
        return super(AccountMove, self).action_invoice_register_payment()

    def validate_bank_account_in_partners(self):
        partners_set = set([move.partner_id for move in self])
        if any(not partner.can_have_payment_posted() for partner in partners_set):
            raise ValidationError(
                _(
                    "You cannot register a payment, if one of the related partners "
                    "does not have only one bank account set up."
                )
            )


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    account_level_1_id = fields.Many2one(
        related="account_id.level_1_id", readonly=True, store=True
    )
    account_level_2_id = fields.Many2one(
        related="account_id.level_2_id", readonly=True, store=True
    )
    account_level_3_id = fields.Many2one(
        related="account_id.level_3_id", readonly=True, store=True
    )
    account_level_4_id = fields.Many2one(
        related="account_id.level_4_id", readonly=True, store=True
    )
    account_level_5_id = fields.Many2one(
        related="account_id.level_5_id", readonly=True, store=True
    )
    account_category_id = fields.Many2one(
        related="account_id.category_id", readonly=True, store=True
    )
    # account_parent_id = fields.Many2one(
    #     related="account_id.parent_id", readonly=True, store=True
    # )
    account_glgroup_id = fields.Many2one(
        related="account_id.glgroup_id", readonly=True, store=True
    )
    account_user_type_id = fields.Many2one(
        related="account_id.user_type_id", readonly=True, store=True
    )
