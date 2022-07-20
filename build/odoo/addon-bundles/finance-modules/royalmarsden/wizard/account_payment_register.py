import logging
import pprint

from odoo import _, models
from odoo.exceptions import ValidationError

_LOGGER = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def get_payments_vals(self):
        payments_vals = super(AccountPaymentRegister, self).get_payments_vals()
        _LOGGER.debug("payments_vals:\n  " + pprint.pformat(payments_vals))
        supplier_payments = filter(
            lambda payment: payment["partner_type"] == "supplier",
            payments_vals,
        )
        if any(payment["payment_type"] == "inbound" for payment in supplier_payments):
            raise ValidationError(_("Negative payments are not allowed"))
        else:
            return payments_vals
