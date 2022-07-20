from odoo import fields, models


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    account_type = fields.Many2one(
        "res.partner.bank.account.type",
        tracking=True,
    )


class ResPartnerBankAccountType(models.Model):
    _name = "res.partner.bank.account.type"
    _description = "Partner Bank Account Type"

    name = fields.Char()
