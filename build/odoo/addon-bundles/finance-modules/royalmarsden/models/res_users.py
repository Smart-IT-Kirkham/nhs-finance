from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _auth_oauth_signin(self, provider, validation, params):
        return (
            super(ResUsers, self)
            .with_context(no_user_creation=True)
            ._auth_oauth_signin(provider, validation, params)
        )

    # Due to Royalmarsden complex access assign. needs to override js method and
    #  create new method to write "Screen Details" in res.users
    #   object with superuser permission.
    def save_screen_details(self, vals):
        if vals:
            self.sudo().write(vals)
        return True
