from odoo import fields, models


class ResBank(models.Model):
    _inherit = "res.bank"

    branch_name = fields.Char()
