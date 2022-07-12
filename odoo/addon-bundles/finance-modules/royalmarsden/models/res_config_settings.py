from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Will be set to False until go-live - where we will update in `apply_royalmarsden_config()`
    default_autogenerate_jac_vsr_number = fields.Boolean(default_model="res.partner")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        param_obj_sudo = self.env["ir.config_parameter"].sudo()
        res.update(
            default_autogenerate_jac_vsr_number=param_obj_sudo.get_param(
                "royalmarsden.default_autogenerate_jac_vsr_number"
            )
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        param_obj_sudo = self.env["ir.config_parameter"].sudo()
        param_obj_sudo.set_param(
            "royalmarsden.default_autogenerate_jac_vsr_number",
            self.default_autogenerate_jac_vsr_number,
        )

    @api.model
    def apply_royalmarsden_config(self):
        if self._needs_to_run():
            self._set_res_config_settings()
            self._update_config_parameter()

    def _set_res_config_settings(self):
        def _set_purchase_config_settings():
            res_config.po_order_approval = True
            res_config.default_purchase_method = "purchase"

        # Sometimes db may not have a res config setting at all!
        if not self.search([]):
            self.create({})
        for res_config in self.search([]):  # Should only be len() 1, but just in case..
            _set_purchase_config_settings()
            res_config.execute()  # Save button.

    def _update_config_parameter(self):
        conf_param_obj = self.env["ir.config_parameter"]
        conf_param_obj.set_param("has_run_royalmarsden_set_config", "True")

    def _needs_to_run(self):
        """
        Determines whether the config setup needs to run based
            on a config parameter.
        Will create config parameter if it does not exist.
        This means we can re-run the config setup by setting the config
            parameter back to false
        """
        conf_param_obj = self.env["ir.config_parameter"]
        has_run_royalmarsden_set_config = conf_param_obj.get_param(
            "has_run_royalmarsden_set_config"
        )
        if has_run_royalmarsden_set_config is not None:
            if has_run_royalmarsden_set_config == "True":
                return False
            else:
                return True
        # If the parameter doesn't exist yet, create it
        conf_param_obj.set_param("has_run_royalmarsden_set_config", "False")
        return True
