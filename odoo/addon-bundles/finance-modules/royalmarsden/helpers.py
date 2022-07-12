def redirect_setupclass_exception(method):
    """
    Decorator to be used like so on setUpClass:
    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):

    Order is important. Redirects raised exceptions from server
    to log and prevents hanging.

    Should be used on all Odoo 13.0 setUpClass functions.

    Ongoing issue which we are trying to find suitable workarounds for.

    See https://github.com/OpusVL/royal-marsden/issues/49 for more detail
    """

    def method_wrapper(*args, **kwargs):
        import logging

        logger = logging.getLogger(__name__)
        try:
            method(*args, **kwargs)
        except Exception:
            logger.exception("setUpClass failed with the following error.")
            logger.error("All tests from this class will fail because of this!")

    return method_wrapper


def reset_config_settings_sysparam(cr):
    """
    Called from migration scripts as it will be a fairly common block.
    If the key doesn't exist, will just UPDATE 0 and the key will
    get created as part of initial install which is intended
    """
    cr.execute(
        """
        UPDATE ir_config_parameter
        SET value='False'
        WHERE key='has_run_royalmarsden_set_config'
    """
    )
