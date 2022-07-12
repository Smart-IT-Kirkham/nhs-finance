from odoo import models

from .. import helpers


class IrModelField(models.Model):
    _inherit = "ir.model.fields"

    def _reflect_field_params(self, field):
        """Setting all the fields from a list in helpers.py to the model
        ir.model.fields tracking True. This function is not enough to create
        logs for the fields to be tracked. For that is inherited
        _get_tracked_fields in mail_thread.py. We are keeping this functionality
        to have consistency in the fields model, so they will be tracking True
        on ir model.fields
        """
        vals = super(IrModelField, self)._reflect_field_params(field)
        model = self.env["ir.model"]._get(field.model_name)
        fields_to_be_tracked = helpers.get_rm_fields_to_be_tracked()
        if model.model in fields_to_be_tracked and vals.get(
            "name"
        ) in fields_to_be_tracked.get(model.model):
            vals.update({"tracking": 100})
        return vals
