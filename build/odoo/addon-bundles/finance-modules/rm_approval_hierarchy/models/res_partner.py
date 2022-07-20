from odoo import _, exceptions, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def write(self, vals):
        """
        bank_ids needs to be required, but because it is a One2Many the
        'required=True' property cannot be used. Check vals for 'bank_ids'
        on write (either virtual or real) and raise an exception if
        not found
        :param vals: <dict>
        :return: super
        """
        super(ResPartner, self).write(vals)
        for record in self:
            # If a supplier and is not a contact of the company
            if (
                record.supplier_rank > 0
                and not record.parent_id
                and not (record.bank_ids or vals.get("bank_ids"))
            ):
                raise exceptions.ValidationError(
                    _("You must add at least one Bank Account!")
                )
