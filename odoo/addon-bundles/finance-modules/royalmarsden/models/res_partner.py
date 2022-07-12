from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    _sql_constraints = [
        (
            "jac_vsr_number_uniq",
            "unique (jac_vsr_number)",
            "JAC VSR Identifier must be unique!",
        )
    ]

    jac_vsr_number = fields.Char(
        string="JAC VSR Identifier",
        help="VSR Identifier as seen in IH JAC import file",
        tracking=True,
    )

    # System field, value configured on res.config.settings
    # with magic default_ field name prefix
    autogenerate_jac_vsr_number = fields.Boolean()

    @api.model
    def create(self, vals):
        if vals.get("autogenerate_jac_vsr_number"):
            vals["jac_vsr_number"] = self.env["ir.sequence"].next_by_code(
                "res.partner.jac.vsr"
            )
        return super(ResPartner, self).create(vals)

    def can_have_payment_posted(self):
        self.ensure_one()
        # fmt: off
        return (
            self.parent_id
            or len(self.bank_ids) == 1
            or self._has_linked_user()
        )
        # fmt: on

    def _has_linked_user(self) -> bool:
        return bool(self.env["res.users"].search([("partner_id", "=", self.id)]))
