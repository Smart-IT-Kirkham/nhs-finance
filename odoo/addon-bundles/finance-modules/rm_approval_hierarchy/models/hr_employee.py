from odoo import models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def update_rm_user_groups(self, job):
        """
        @param job: hr.job record set
        Propagate the res group defined against the `job`s to the
        users which are linked to the employee(s) under self
        """
        users = self.mapped("user_id")
        all_rm_groups = self.env["res.groups"].search(
            [("rm_approval_group", "=", True)]
        )
        for remaining_group in all_rm_groups.filtered(
            lambda group: group == job.group_id
        ):
            users.write(dict(groups_id=[(3, remaining_group.id)]))
        users.write(dict(groups_id=[(4, job.group_id.id)]))
        return True

    def action_approve(self):
        res = super(HrEmployee, self).action_approve()
        if self.job_id and self.job_id.group_id and self.job_id.state == "approved":
            self.update_rm_user_groups(self.job_id)
        return res
