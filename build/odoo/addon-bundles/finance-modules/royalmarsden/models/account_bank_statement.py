from odoo import fields, models


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    created_via_bankline_import = fields.Boolean(readonly=True)


class BankStatementLineType(models.Model):
    _name = "bank.statement.line.type"

    name = fields.Char(string="Name", required=True)

    _sql_constraints = [
        (
            "name_uniq",
            "unique(name)",
            "The name of the bank statement line type must be unique!",
        )
    ]


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    narrative_one = fields.Char(
        string="Narrative 1",
    )
    narrative_two = fields.Char(
        string="Narrative 2",
    )
    narrative_three = fields.Char(
        string="Narrative 3",
    )
    narrative_four = fields.Char(
        string="Narrative 4",
    )
    narrative_five = fields.Char(
        string="Narrative 5",
    )
    line_type_id = fields.Many2one(
        "bank.statement.line.type", "Bank Statement Line Type"
    )
