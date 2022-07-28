# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # state = fields.Selection(
    #     selection_add=[
    #         ('waiting', 'Waiting'),
    #     ],
    # )
