from odoo import api, fields, models


class AccountBudget(models.Model):
    _name = "account.budget"
    _description = "Account Budget Configuration"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        "Budget Name",
        required=True,
        states={"done": [("readonly", True)], "cancel": [("readonly", True)]},
        tracking=True,
    )
    complete_name = fields.Char(
        "Full Budget Name", compute="_compute_complete_name", store=True
    )
    user_id = fields.Many2one(
        "res.users",
        "Responsible",
        default=lambda self: self.env.uid,
        tracking=True,
    )
    budget_line = fields.One2many(
        "account.budget.line",
        "budget_id",
        "Budget Lines",
        states={"done": [("readonly", True)], "cancel": [("readonly", True)]},
        copy=True,
    )
    company_id = fields.Many2one(
        "res.company", "Company", default=lambda self: self.env.company
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("cancel", "Cancelled"),
            ("confirm", "Confirmed"),
            ("validate", "Validated"),
            ("done", "Done"),
        ],
        "Status",
        default="draft",
        index=True,
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
    )
    type = fields.Selection(
        [
            ("other", "Regular"),
            ("view", "View"),
        ],
        required=True,
        states={"done": [("readonly", True)], "cancel": [("readonly", True)]},
        default="other",
    )
    parent_id = fields.Many2one(
        "account.budget",
        "Parent Budget",
        states={"done": [("readonly", True)], "cancel": [("readonly", True)]},
        tracking=True,
        ondelete="set null",
    )
    fiscalyear_id = fields.Many2one(
        "account.fiscalyear",
        "Fiscal Year",
        tracking=True,
        required=True,
        states={"done": [("readonly", True)], "cancel": [("readonly", True)]},
    )
    description = fields.Char(
        string="Description",
        tracking=True,
        states={"done": [("readonly", True)], "cancel": [("readonly", True)]},
    )
    child_ids = fields.One2many("account.budget", "parent_id", "Direct children")

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for budget in self:
            if budget.parent_id and budget.type != "view":
                budget.complete_name = "%s/%s" % (
                    budget.parent_id.complete_name,
                    budget.name,
                )
            else:
                budget.complete_name = budget.name

    @api.onchange("parent_id")
    def _onchange_parent_id(self):
        self.fiscalyear_id = self.parent_id.fiscalyear_id

    def action_budget_confirm(self):
        self.write({"state": "confirm"})

    def action_budget_draft(self):
        self.write({"state": "draft"})

    def action_budget_validate(self):
        self.write({"state": "validate"})

    def action_budget_cancel(self):
        self.write({"state": "cancel"})

    def action_budget_done(self):
        self.write({"state": "done"})


class AccountBudgetLine(models.Model):
    _name = "account.budget.line"
    _description = "Account Budget Lines"

    budget_id = fields.Many2one(
        "account.budget",
        string="Account Budget",
        index=True,
        required=True,
        readonly=True,
        auto_join=True,
        ondelete="cascade",
        help="The budget of this entry line.",
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account", "Analytic Account"
    )
    account_id = fields.Many2one("account.account", "Account")
    company_id = fields.Many2one(related="budget_id.company_id", store=True, index=True)
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", store=True, readonly=True
    )
    planned_amount = fields.Monetary(
        "Budget",
        required=True,
        help="Amount you plan to earn/spend. Record a positive amount if it is "
        "a revenue and a negative amount if it is a cost.",
    )
    period_id = fields.Many2one("account.period", "Period")
    fiscalyear_id = fields.Many2one(
        "account.fiscalyear",
        related="budget_id.fiscalyear_id",
        readonly=True,
        store=True,
    )
    type = fields.Selection(
        related="budget_id.type",
        readonly=True,
        store=True,
    )
    state = fields.Selection(
        related="budget_id.state",
        readonly=True,
        store=True,
    )
    user_id = fields.Many2one(
        "res.users",
        related="budget_id.user_id",
        readonly=True,
        store=True,
    )

    _sql_constraints = [
        (
            "budget_line_unique",
            "unique (analytic_account_id,company_id, period_id, account_id, budget_id)",
            "Budget line with these combinations already exists !",
        )
    ]
