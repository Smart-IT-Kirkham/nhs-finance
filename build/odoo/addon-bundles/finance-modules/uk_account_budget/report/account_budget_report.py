from psycopg2.extensions import AsIs

from odoo import api, fields, models, tools


class VarianceBudgetReport(models.Model):
    _name = "variance.budget.report"
    _description = "Budget Statistics"
    _auto = False
    _rec_name = "account_id"
    _order = "date_start desc, date_period_start desc"

    budget_id = fields.Many2one("account.budget", readonly=True)
    period = fields.Many2one("account.period", readonly=True)
    cost_center = fields.Many2one(
        "account.analytic.account", string="Analytic Account", readonly=True
    )
    planned_amount = fields.Float(
        string="Planned Amount",
        readonly=True,
    )
    balance = fields.Float(
        string="Balance",
        readonly=True,
    )
    account_id = fields.Many2one("account.account", readonly=True)
    parent_id = fields.Many2one("account.budget", readonly=True)
    cmp_id = fields.Many2one("res.company", string="Company", readonly=True)
    crc_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    user_id = fields.Many2one("res.users", string="Responsible", readonly=True)
    budget_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("cancel", "Cancelled"),
            ("confirm", "Confirmed"),
            ("validate", "Validated"),
            ("done", "Done"),
        ],
        string="Budget Status",
        readonly=True,
    )
    difference_amount = fields.Float(
        string="Variance",
        readonly=True,
    )
    level_1_id = fields.Many2one(
        "account.account.hierarchy", string="Level 1", readonly=True
    )
    level_2_id = fields.Many2one(
        "account.account.hierarchy", string="Level 2", readonly=True
    )
    level_3_id = fields.Many2one(
        "account.account.hierarchy", string="Level 3", readonly=True
    )
    level_4_id = fields.Many2one(
        "account.account.hierarchy", string="Level 4", readonly=True
    )
    level_5_id = fields.Many2one(
        "account.account.hierarchy", string="Level 5", readonly=True
    )
    glgroup_id = fields.Many2one(
        "account.account.glgroup", string="Group", readonly=True
    )
    user_type_id = fields.Many2one(
        "account.account.type", string="Account Type", readonly=True
    )
    fiscalyear_id = fields.Many2one("account.fiscalyear", readonly=True)
    type = fields.Selection(
        [
            ("other", "Regular"),
            ("view", "View"),
        ],
        string="Type",
        readonly=True,
    )
    date_start = fields.Date(readonly=True, string="Date Start")
    date_stop = fields.Date(readonly=True, string="Date Stop")
    date_period_start = fields.Date(readonly=True, string="Date Period Start")
    date_period_stop = fields.Date(readonly=True, string="Date Period Stop")
    date_posted = fields.Date(readonly=True, string="Date Posted")

    _depends = {
        "account.move": [
            "name",
            "state",
            "type",
            "period_id",
            "date",
        ],
        "account.move.line": [
            "debit",
            "credit",
            "analytic_account_id",
            "account_id",
            "balance" "company_id",
            "name",
            "account_level_1_id",
            "account_level_2_id",
            "account_level_3_id",
            "account_level_4_id",
            "account_level_5_id",
            "account_glgroup_id",
            "account_user_type_id",
        ],
        "account.budget": ["parent_id", "fiscalyear_id"],
        "account.budget.line": [
            "budget_id",
            "analytic_account_id",
            "account_id",
            "company_id",
            "planned_amount",
            "period_id",
            "fiscalyear_id",
            "type",
            "state",
            "user_id",
        ],
        "account.account": ["name", "code"],
        "account.analytic.account": ["name"],
    }

    @api.model
    def _select(self):
        return """
            SELECT
                account.id,
                account.id as account_id,
                budget.id as budget_id,
                budget.user_id,
                budget.parent_id,
                budget.state as budget_state,
                budget.type,
                account.level_1_id,
                account.level_2_id,
                account.level_3_id,
                account.level_4_id,
                account.level_5_id,
                account.glgroup_id,
                account.user_type_id,
                fiscal.id as fiscalyear_id,
                pr.id as period,
                bline.analytic_account_id as cost_center,
                COALESCE(AVG(bline.planned_amount), 0.0) as planned_amount,
                COALESCE(SUM(mline.balance), 0.0) as balance,
                COALESCE(SUM(mline.balance) - AVG(bline.planned_amount), 0)
                    as difference_amount,
                coalesce(mline.company_id, bline.company_id) as cmp_id,
                coalesce(mline.currency_id, bline.currency_id) as crc_id,
                mline.date as date_posted,
                fiscal.date_start,
                fiscal.date_stop,
                pr.date_start as date_period_start,
                pr.date_stop as date_period_stop
            """

    @api.model
    def _from(self):
        return """
                FROM account_account account
                LEFT JOIN account_move_line mline
                On mline.account_id = account.id and mline.state = 'posted'
                LEFT JOIN account_budget_line bline
                ON bline.account_id = account.id
                LEFT JOIN account_budget budget
                ON bline.budget_id = budget.id
                LEFT JOIN account_period pr
                ON pr.id = bline.period_id
                LEFT JOIN account_fiscalyear fiscal
                ON fiscal.id = pr.fiscalyear_id
            """

    @api.model
    def _group_by(self):
        return """
        GROUP BY
             account.id,
             budget.id,
             fiscal.id,
             period,
             date_period_start,
             date_period_stop,
             date_posted,
             cost_center,
             cmp_id,
             crc_id
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
                CREATE OR REPLACE VIEW %s AS (
                    %s %s %s
                )
            """,
            (
                AsIs(self._table),
                AsIs(self._select()),
                AsIs(self._from()),
                AsIs(self._group_by()),
            ),
        )
