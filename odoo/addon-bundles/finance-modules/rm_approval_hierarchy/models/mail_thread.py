from odoo import api, models

from .. import helpers


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def _get_tracked_fields(self):
        """Return a structure of tracked fields for the current model.
        :return dict: a dict mapping field name to description, containing on_change fields
        """
        result = super(MailThread, self)._get_tracked_fields()
        tracked_fields = []
        fields_to_be_tracked = helpers.get_rm_fields_to_be_tracked()
        if self._name in fields_to_be_tracked:
            for name, _field in self._fields.items():
                if name not in result and name in fields_to_be_tracked.get(self._name):
                    tracked_fields.append(name)
        if tracked_fields:
            result.update(self.fields_get(tracked_fields))
        return result
