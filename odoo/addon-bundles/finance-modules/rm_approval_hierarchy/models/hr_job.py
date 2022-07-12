from odoo import fields, models

from .. import helpers


class HrJob(models.Model):
    _inherit = "hr.job"

    group_id = fields.Many2one(
        "res.groups", string="User Group", domain=[("rm_approval_group", "=", True)]
    )

    def action_approve(self):
        res = super(HrJob, self).action_approve()
        if self.group_id:
            self.employee_ids.update_rm_user_groups(job=self)
        return res

    def write(self, vals):
        fields_to_be_tracked = helpers.get_rm_fields_to_be_tracked()
        if any(field in vals for field in fields_to_be_tracked.get("hr.job")):
            vals["state"] = "draft"
        return super(HrJob, self).write(vals)
