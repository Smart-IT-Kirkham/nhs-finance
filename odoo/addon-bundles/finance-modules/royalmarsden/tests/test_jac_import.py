import base64
import datetime
import logging
import os

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import Form, SavepointCase

from ..helpers import redirect_setupclass_exception


class JacImportCommon(SavepointCase):
    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(JacImportCommon, cls).setUpClass()
        cls._load_files_to_memory()
        account_user_group = cls.env.ref("account.group_account_invoice")
        cls.demo_user = cls.env.ref("base.user_demo")
        cls.purchase_user = cls.env.ref("base.user_demo").copy()
        # Give demo user account user permissions
        account_user_group.write(
            dict(users=[(4, cls.demo_user.id), (3, cls.purchase_user.id)])
        )
        cls.jac_obj = cls.env["account.jac.import"].with_user(cls.demo_user)
        cls.move_obj = cls.env["account.move"]
        cls.move_line_obj = cls.env["account.move.line"]
        cls.logger = logging.getLogger(__name__)
        # This is a configuration step that will be performed by RM but is required
        # for the tests to pass
        cls.env["account.payment.term"].search([("name", "=", "30 Days")]).write(
            dict(jac_import_payment_term_name="30 DAYS NET")
        )
        # Same for tax mapping
        cls.env["account.tax"].search(
            [("name", "=", "Standard rate purchases (20%)")]
        ).write(dict(jac_import_tax_name="Standard", price_include=True))
        cls.env["account.tax"].search([("name", "=", "Zero rated purchases")]).write(
            dict(jac_import_tax_name="Zero", price_include=True)
        )

        cls.fiscal_year_obj = cls.env["account.fiscalyear"]
        fiscal_year_2020 = cls.fiscal_year_obj.create(
            dict(
                name="2020",
                code="2020",
                date_start="2020-01-01",
                date_stop="2020-12-31",
            )
        )
        fiscal_year_2020.create_period()

    @classmethod
    def _load_files_to_memory(cls):
        base_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "jac_import_files"
        )
        filenames = [
            "INVALID_JAC",
            "INVALID_JAC_NO_IH_OR_TL",
            "INVALID_JAC_INCORRECT_COLUMNS",
            "INVALID_JAC_NO_ACCOUNT",
            "INVALID_JAC_NO_SUPPLIER",
            "INVALID_JAC_BAD_LOOKUP_CODE",
            "INVALID_JAC_BAD_PRICES",
            "INVALID_JAC_BAD_PAYMENT_TERMS",
            "INVALID_JAC_BAD_DISCOUNT",
            "INVALID_JAC_BAD_TAX",
            "WORKING_SAMPLE",
            "WORKING_SAMPLE_SMALL",
            "WORKING_SAMPLE_TAX_LINES",
            "WORKING_SAMPLE_REFUND",
        ]
        path_file_mapping = {}
        for filename in filenames:
            with open(os.path.join(base_path, filename), "rb") as file:
                path_file_mapping[filename] = base64.b64encode(file.read())
        cls.path_file_mapping = path_file_mapping


# ------------------ PREFLIGHT TESTS ---------------------
class JacPreflightWorkingJacDuplicateInvoiceRef(JacImportCommon):
    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(JacPreflightWorkingJacDuplicateInvoiceRef, cls).setUpClass()
        # This ref exists in the WORKING_SAMPLE
        invoice = Form(cls.env["account.move"])
        invoice.ref = "VF01-01-201330"
        cls.invoice_a = invoice.save()
        cls.jac_wizard = Form(cls.jac_obj)
        cls.jac_wizard.input_file = cls.path_file_mapping.get("WORKING_SAMPLE")

    def test_duplicate_invoice_exception(self):
        with self.assertRaises(ValidationError) as cm:
            wizard_rec = self.jac_wizard.save()
            wizard_rec.import_jac_file()
        self.logger.debug(cm.exception)


class JacPreflightBrokenJac(JacImportCommon):
    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(JacPreflightBrokenJac, cls).setUpClass()
        cls.expected_failure_files = [
            "INVALID_JAC",
            "INVALID_JAC_NO_IH_OR_TL",
            "INVALID_JAC_INCORRECT_COLUMNS",
            "INVALID_JAC_NO_ACCOUNT",
            "INVALID_JAC_NO_SUPPLIER",
            "INVALID_JAC_BAD_LOOKUP_CODE",
            "INVALID_JAC_BAD_PRICES",
            "INVALID_JAC_BAD_PAYMENT_TERMS",
            "INVALID_JAC_BAD_DISCOUNT",
            "INVALID_JAC_BAD_TAX",
        ]

    def test_invalid_jac_exception(self):
        for expected_failure_file in self.expected_failure_files:
            jac_wizard = Form(self.jac_obj)
            jac_wizard.input_file = self.path_file_mapping.get(expected_failure_file)
            with self.assertRaises(ValidationError) as cm:
                wizard_rec = jac_wizard.save()
                wizard_rec.import_jac_file()
            self.logger.debug(cm.exception)


class JacPreflightWrongPermission(JacImportCommon):
    def test_access_error(self):
        with self.assertRaises(AccessError) as cm:
            # This with_user overrides the one set up on self.jac_obj in JacImportCommon
            jac_wizard = self.jac_obj.with_user(self.purchase_user).create(
                dict(input_file=self.path_file_mapping.get("WORKING_SAMPLE"))
            )
            jac_wizard.import_jac_file()
        self.logger.debug(cm.exception)


# ------------------ IMPORT TESTS ---------------------
class JacImportWorkingJac(JacImportCommon):
    """
    High level check whether generally, the import worked for multiple moves
    """

    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(JacImportWorkingJac, cls).setUpClass()
        jac_wizard = Form(cls.jac_obj)
        jac_wizard.input_file = cls.path_file_mapping.get("WORKING_SAMPLE")
        cls.wizard_rec = jac_wizard.save()
        cls.wizard_rec.import_jac_file()
        cls.created_moves = cls.move_obj.search([("created_via_jac_import", "=", True)])
        cls.created_move_lines = cls.created_moves.mapped("invoice_line_ids")

    def test_vendor_bill_suppliers_are_mostly_different(self):
        # There are 6 unique JAC VSR numbers in the WORKING_SAMPLE
        self.assertEqual(len(self.created_moves.mapped("partner_id")), 6)

    def test_all_moves_created(self):
        self.assertEqual(len(self.created_moves), 8)
        self.assertTrue(all(move.state == "posted" for move in self.created_moves))

    def test_move_lines_created(self):
        self.assertEqual(len(self.created_move_lines), 12)

    def test_audit_log_created(self):
        self.assertEqual(len(self.env["account.jac.import.log"].search([])), 1)


class JacImportWorkingSubset(JacImportCommon):
    """
    More granular check for a single move whether values look correct
    """

    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(JacImportWorkingSubset, cls).setUpClass()
        jac_wizard = Form(cls.jac_obj)
        jac_wizard.input_file = cls.path_file_mapping.get("WORKING_SAMPLE_SMALL")
        jac_wizard.input_name = "WORKING_SAMPLE_SMALL"  # Usually handled in GUI
        cls.wizard_rec = jac_wizard.save()
        cls.wizard_rec.import_jac_file()
        cls.created_move = cls.move_obj.search([("created_via_jac_import", "=", True)])
        cls.created_move_lines = cls.created_move.mapped("invoice_line_ids")

    def test_audit_log_values(self):
        audit_log = self.env["account.jac.import.log"].search([])
        self.assertEqual(len(audit_log), 1)
        # FIXME: Datetime cannot round, May just scrap this test as i'm just asserting
        # datetime works, and the test is likely to fail because of this
        # self.assertAlmostEqual(audit_log.date_of_import, datetime.datetime.today())
        self.assertEqual(audit_log.jac_header_row_count, 1)
        self.assertEqual(audit_log.jac_line_row_count, 3)
        self.assertEqual(audit_log.name, "WORKING_SAMPLE_SMALL")
        self.assertAlmostEqual(audit_log.jac_header_total, 53.26)
        self.assertAlmostEqual(audit_log.jac_lines_total, 53.26)
        self.assertEqual(audit_log.user_id, self.demo_user)

    def test_individual_move_values(self):
        move = self.created_move
        self.assertEqual(
            move.partner_id, self.env.ref("royalmarsden.rm_demo_partner_13")
        )
        self.assertEqual(move.journal_id.name, "Vendor Bills")
        self.assertEqual(move.ref, "A02W00965")
        self.assertEqual(move.type, "in_invoice")
        self.assertEqual(move.date, datetime.date(2020, 3, 4))
        self.assertEqual(move.invoice_date, datetime.date(2020, 2, 18))
        self.assertEqual(
            move.invoice_payment_term_id,
            self.env.ref("account.account_payment_term_30days"),
        )
        self.assertEqual(move.discount_amount, 5)
        self.assertTrue(move.created_via_jac_import)
        self.assertTrue(move.jac_prime_key)
        self.assertTrue(move.jac_import_token)
        line_total_sum = sum(self.created_move_lines.mapped("price_total"))
        # TODO: This test may be incorrect. I'm not 100% clear how this should work
        self.assertEqual(
            move.amount_total, round(line_total_sum - move.discount_amount, 2)
        )
        self.assertEqual(move.discount_amt, 5)
        # O2521, DB raised the amount due is not taking into account the discount
        self.assertEqual(move.amount_residual, move.amount_total)

    def test_individual_move_line_values(self):
        move_lines = self.created_move_lines
        ml_1 = move_lines[0]
        ml_2 = move_lines[1]
        ml_3 = move_lines[2]
        # Common values across all lines
        for move_line in move_lines:
            self.assertEqual(
                move_line.product_id, self.env.ref("royalmarsden.rm_product_drugs")
            )
            self.assertEqual(move_line.account_id.code, "1110")
            self.assertEqual(move_line.credit, 0)

        # We round the price_unit and debit because odoo is messing with
        # the values post-import to result in values like 2.280000000002.
        # This is actually fine and there's nothing we can do about it
        # (even if we round before writing to the db)
        self.assertEqual(ml_1.name, "5 Patch Box FENTANYL Patch 100microgram/hour")
        self.assertEqual(ml_1.quantity, 1)
        self.assertAlmostEqual(ml_1.price_unit, 14.4)
        self.assertAlmostEqual(ml_1.debit, 12.0)
        self.assertAlmostEqual(ml_1.price_total, 14.4)

        self.assertEqual(ml_2.name, "5 Patch Box FENTANYL Patch 25microgram/hour")
        self.assertEqual(ml_2.quantity, 1)
        self.assertAlmostEqual(ml_2.price_unit, 6.84)
        self.assertAlmostEqual(ml_2.debit, 5.7)
        self.assertAlmostEqual(ml_2.price_total, 6.84)

        self.assertEqual(
            ml_3.name, "30 Tablet Pack MIRABEGRON Modified Release Tablets 50mg"
        )
        self.assertEqual(ml_3.quantity, 1)
        self.assertAlmostEqual(ml_3.price_unit, 32.02)
        self.assertAlmostEqual(ml_3.debit, 26.68)
        self.assertAlmostEqual(ml_3.price_total, 32.02)


class JacImportWorkingTwice(JacImportCommon):
    """
    Import the same working small sample twice. Expected failure
    """

    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(JacImportWorkingTwice, cls).setUpClass()
        in_filename = "WORKING_SAMPLE_SMALL"
        in_file = cls.path_file_mapping.get(in_filename)

        jac_wizard = Form(cls.jac_obj)
        jac_wizard.input_file = in_file
        jac_wizard.input_name = in_filename
        wizard_rec = jac_wizard.save()
        wizard_rec.import_jac_file()

        jac_wizard_2 = Form(cls.jac_obj)
        jac_wizard_2.input_file = in_file
        jac_wizard_2.input_name = in_filename
        cls.jac_wizard_2 = jac_wizard_2.save()

    def test_importing_same_file_twice_raises(self):
        with self.assertRaises(ValidationError) as cm:
            self.jac_wizard_2.import_jac_file()
        self.logger.debug(cm.exception)


class JacImportWorkingRefund(JacImportCommon):
    """
    Ensure invoice type is in_refund when type (col 6) is not STANDARD
    """

    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(JacImportWorkingRefund, cls).setUpClass()
        jac_wizard = Form(cls.jac_obj)
        jac_wizard.input_file = cls.path_file_mapping.get("WORKING_SAMPLE_REFUND")
        cls.wizard_rec = jac_wizard.save()
        cls.wizard_rec.import_jac_file()
        cls.created_move = cls.move_obj.search([("created_via_jac_import", "=", True)])
        cls.created_move_lines = cls.created_move.mapped("invoice_line_ids")

    def test_move_is_refund(self):
        self.assertEqual(self.created_move.type, "in_refund")
        # Ensure non-negative value despite negative value in file
        self.assertEqual(self.created_move.amount_total, 48.26)


class JacImportWorkingTaxLines(JacImportCommon):
    """
    Ensure tax lines are ignored
    """

    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(JacImportWorkingTaxLines, cls).setUpClass()
        jac_wizard = Form(cls.jac_obj)
        jac_wizard.input_file = cls.path_file_mapping.get("WORKING_SAMPLE_TAX_LINES")
        cls.wizard_rec = jac_wizard.save()
        cls.wizard_rec.import_jac_file()
        cls.created_move = cls.move_obj.search([("created_via_jac_import", "=", True)])
        cls.created_move_lines = cls.created_move.mapped("invoice_line_ids")

    def test_no_move_lines(self):
        self.assertEqual(len(self.created_move_lines), 1)
