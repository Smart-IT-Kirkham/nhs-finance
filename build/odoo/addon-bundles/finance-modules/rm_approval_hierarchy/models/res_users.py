from odoo import fields, models


class Groups(models.Model):
    _inherit = "res.groups"

    rm_approval_group = fields.Boolean(
        string="RM Approval Group",
    )

    def _get_hidden_extra_categories(self):
        result = super(Groups, self)._get_hidden_extra_categories()
        result.append("rm_approval_hierarchy.module_category_rm_approval_hierarchy")
        return result
