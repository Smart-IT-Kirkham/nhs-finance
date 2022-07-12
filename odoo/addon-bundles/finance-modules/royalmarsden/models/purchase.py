from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    validation_date = fields.Date(readonly=True, copy=False)
    validated_by_id = fields.Many2one(
        "hr.employee", readonly=True, string="Validated By", copy=False
    )
    buyer_id = fields.Many2one("hr.employee", string="Buyer")

    def button_approve(self, force=False):
        res = super(PurchaseOrder, self).button_approve(force=force)
        self.validation_date = fields.Datetime.now()
        self.validated_by_id = self.env.user.employee_id
        return res

    def action_view_invoice(self):
        """
        default_purchase_id is already set by the standard function call,
        however - it is used to propagate the purchase lines into the new bill
        and then is cleared once propagation is complete.
        For this reason, we need a new column to link back to the origin purchase
        """
        res = super(PurchaseOrder, self).action_view_invoice()
        create_bill = self.env.context.get("create_bill", False)
        if create_bill:
            res.get("context")["default_created_from_purchase_id"] = self.id
        return res
