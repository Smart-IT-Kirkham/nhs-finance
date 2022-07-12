from odoo import _, models
from odoo.exceptions import AccessError


class AccountBanklineImport(models.TransientModel):
    _inherit = "account.bankline.import"

    # Override from rm module
    def check_import_bankline_right(self):
        if not self.env.su and not self.env.user.has_group(
            "approval_hierarchy.import_bank_statement_role"
        ):
            raise AccessError(
                _("You don't have access rights to perform a Bankline Import.")
            )
