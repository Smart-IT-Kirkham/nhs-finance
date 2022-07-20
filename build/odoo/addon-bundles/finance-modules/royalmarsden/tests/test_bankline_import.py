import base64
import logging
import os

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import Form, SavepointCase

from ..helpers import redirect_setupclass_exception


class BanklineImportCommon(SavepointCase):
    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(BanklineImportCommon, cls).setUpClass()
        cls._load_files_to_memory()
        cls.bankstatement_obj = cls.env["account.bank.statement"]
        cls.demo_user = cls.env.ref("base.user_demo")
        cls.purchase_user = cls.env.ref("base.user_demo").copy()
        # Give demo user account manager permissions
        cls.env.ref("account.group_account_manager").write(
            dict(users=[(4, cls.demo_user.id)])
        )
        # Also give them 'Show Full Accounting Features
        # This confused me at first because the group id does not reflect the
        # functionality at all. I incorrectly assumed group_account_manager implies
        # group_account_user but that is incorrect, it implies group_account_invoice.
        # group_account_user is seperate!
        # Checking if rm_approval_hierarchy is in installed or to upgrade
        if cls.env["ir.module.module"].search(
            [
                ("name", "=", "rm_approval_hierarchy"),
                ("state", "in", ["to upgrade", "installed"]),
            ],
            limit=1,
        ):
            cls.env.ref("approval_hierarchy.import_bank_statement_role").write(
                dict(users=[(4, cls.demo_user.id)])
            )
        else:
            cls.env.ref("account.group_account_user").write(
                dict(users=[(4, cls.demo_user.id)])
            )
        # Perform anything bankline_obj related as a
        # basic user with accounting permissions
        cls.bankline_obj = cls.env["account.bankline.import"].with_user(cls.demo_user)
        cls.logger = logging.getLogger(__name__)
        # Data required for the WORKING_SAMPLE(_SMALL) to work
        for supplier_name in ["RM", "BANKLINE"]:
            cls.env["res.partner"].create(dict(name=supplier_name, supplier_rank=1))

        # We will simulate setting up the bank data via the GUI
        # to ensure the customer will be able to do the same.
        bank_form = Form(cls.env["res.bank"])
        bank_form.bic = "RBI244L"
        bank_form.name = "Royal Bank of Scotland"
        bank_form.branch_name = "London Street"
        rbs_bank = bank_form.save()

        # This is the Add a Bank Account wizard
        new_bank_form = Form(cls.env["account.setup.bank.manual.config"])
        new_bank_form.new_journal_name = "Test Bank Journal"
        new_bank_form.acc_number = "123456789"
        new_bank_form.bank_id = rbs_bank
        new_bank_form.new_journal_code = "TBJ1"
        new_bank_wizard = new_bank_form.save()
        new_bank_wizard.validate()
        cls.created_journal = cls.env["account.journal"].search(
            [("bank_acc_number", "=", "123456789")]
        )

        partner_bank = cls.created_journal.bank_account_id
        partner_bank_form = Form(partner_bank)
        partner_bank_form.acc_number = "45236723"
        partner_bank_form.sort_code = "18705"
        partner_bank_form.acc_holder_name = "RMP"
        partner_bank_form.short_name = "Royal Marsden Pharmacy"
        partner_bank_form.account_type = cls.env.ref(
            "royalmarsden.bank_account_type_select_account"
        )
        partner_bank_form.save()
        cls.bank_line_type_obj = cls.env["bank.statement.line.type"]
        cls.bank_line_type_obj.create(
            dict(
                name="BLN",
            )
        )
        cls.bank_line_type_obj.create(
            dict(
                name="BAC",
            )
        )

    @classmethod
    def _load_files_to_memory(cls):
        base_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "bankline_import_files"
        )
        filenames = [
            "WORKING_SAMPLE",
            "WORKING_SAMPLE_SMALL",
            "INVALID_BANKLINE_NONEXISTENT_ACCOUNT",
            "INVALID_BANKLINE_NONEXISTENT_SORTCODE",
            "INVALID_BANKLINE_NONEXISTENT_TYPE",
            "INVALID_BANKLINE_NONEXISTENT_ACCOUNT_ALIAS",
            "INVALID_BANKLINE_NONEXISTENT_BRANCHNAME",
            "INVALID_BANKLINE_NONEXISTENT_BANKNAME",
            "INVALID_BANKLINE_NONEXISTENT_BIC",
            "INVALID_BANKLINE_NONEXISTENT_PARTNER",
            "INVALID_BANKLINE_WRONG_NUMBER_OF_COLUMNS",
            "INVALID_BANKLINE_BAD_FLOAT",
            "INVALID_BANKLINE_NONEQUAL_ACCOUNTDETAILS",
        ]
        path_file_mapping = {}
        for filename in filenames:
            with open(os.path.join(base_path, filename), "rb") as file:
                path_file_mapping[filename] = base64.b64encode(file.read())
        cls.path_file_mapping = path_file_mapping


# ------------------ PREFLIGHT TESTS ---------------------
class BanklinePreflightBrokenBankline(BanklineImportCommon):
    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(BanklinePreflightBrokenBankline, cls).setUpClass()
        cls.expected_failure_files = [
            "INVALID_BANKLINE_NONEXISTENT_ACCOUNT",
            "INVALID_BANKLINE_NONEXISTENT_SORTCODE",
            "INVALID_BANKLINE_NONEXISTENT_TYPE",
            "INVALID_BANKLINE_NONEXISTENT_ACCOUNT_ALIAS",
            "INVALID_BANKLINE_NONEXISTENT_BRANCHNAME",
            "INVALID_BANKLINE_NONEXISTENT_BANKNAME",
            "INVALID_BANKLINE_NONEXISTENT_BIC",
            "INVALID_BANKLINE_NONEXISTENT_PARTNER",
            "INVALID_BANKLINE_WRONG_NUMBER_OF_COLUMNS",
            "INVALID_BANKLINE_BAD_FLOAT",
            "INVALID_BANKLINE_NONEQUAL_ACCOUNTDETAILS",
        ]

    def test_invalid_bankline_exception(self):
        for expected_failure_file in self.expected_failure_files:
            bankline_wizard = Form(self.bankline_obj)
            bankline_wizard.input_file = self.path_file_mapping.get(
                expected_failure_file
            )
            with self.assertRaises(ValidationError) as cm:
                wizard_rec = bankline_wizard.save()
                wizard_rec.import_bankline_file()
            self.logger.debug(cm.exception)


# Needs to discuss with Narender that in case that are more
# than one partner with the same code what should be done
# class BanklinePreflightDuplicatePartner(BanklinePreflightBrokenBankline):
#     @classmethod
#     @redirect_setupclass_exception
#     def setUpClass(cls):
#         super(BanklinePreflightDuplicatePartner, cls).setUpClass()
#         cls.expected_failure_files = [
#             'WORKING_SAMPLE',
#         ]
#         # Create the partners again, so that we have duplicates, and the
#         # import should fail when parent class test is run
#         for supplier_name in ['RM', 'BANKLINE']:
#             cls.env['res.partner'].create(dict(
#                 name=supplier_name,
#                 supplier_rank=1))


class BanklinePreflightWrongPermission(BanklineImportCommon):
    def test_access_error(self):
        with self.assertRaises(AccessError) as cm:
            # This with_user overrides the one set up on
            # self.bankline_obj in BanklineImportCommon
            bankline_wizard = self.bankline_obj.with_user(self.purchase_user).create(
                dict(input_file=self.path_file_mapping.get("WORKING_SAMPLE"))
            )
            bankline_wizard.import_bankline_file()
        self.logger.debug(cm.exception)


class BanklineImportWorkingTwice(BanklineImportCommon):
    """
    Import the same working small sample twice. Expected failure
    """

    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(BanklineImportWorkingTwice, cls).setUpClass()
        in_filename = "WORKING_SAMPLE_SMALL"
        in_file = cls.path_file_mapping.get(in_filename)

        bankline_wizard = Form(cls.bankline_obj)
        bankline_wizard.input_file = in_file
        bankline_wizard.input_name = in_filename
        wizard_rec = bankline_wizard.save()
        wizard_rec.import_bankline_file()

        bankline_wizard_2 = Form(cls.bankline_obj)
        bankline_wizard_2.input_file = in_file
        bankline_wizard_2.input_name = in_filename
        cls.bankline_wizard_2 = bankline_wizard_2.save()

    def test_importing_same_file_twice_raises(self):
        with self.assertRaises(ValidationError) as cm:
            self.bankline_wizard_2.import_bankline_file()
        self.logger.debug(cm.exception)


# ------------------ IMPORT TESTS ---------------------
class BanklineImportWorkingBankline(BanklineImportCommon):
    """
    High level check whether generally, the import worked for a large sample file
    """

    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(BanklineImportWorkingBankline, cls).setUpClass()
        bankline_wizard = Form(cls.bankline_obj)
        bankline_wizard.input_file = cls.path_file_mapping.get("WORKING_SAMPLE")
        bankline_wizard.input_name = "WORKING_SAMPLE"  # Usually handled in GUI
        cls.wizard_rec = bankline_wizard.save()
        cls.wizard_rec.import_bankline_file()
        cls.created_bankstatement = cls.bankstatement_obj.search(
            [("created_via_bankline_import", "=", True)]
        )

    def test_bankstatement_created(self):
        self.assertEqual(len(self.created_bankstatement), 1)
        self.assertEqual(len(self.created_bankstatement.line_ids), 2)

    def test_audit_log_created(self):
        self.assertEqual(len(self.env["account.bankline.import.log"].search([])), 1)

    def test_audit_log_values(self):
        audit_log = self.env["account.bankline.import.log"].search([])
        self.assertEqual(len(audit_log), 1)
        self.assertEqual(audit_log.name, "WORKING_SAMPLE")
        self.assertEqual(audit_log.bankline_row_count, 2)


class BanklineImportWorkingSubset(BanklineImportCommon):
    """
    More granular check for a small file whether values look correct
    """

    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(BanklineImportWorkingSubset, cls).setUpClass()
        bankline_wizard = Form(cls.bankline_obj)
        bankline_wizard.input_file = cls.path_file_mapping.get("WORKING_SAMPLE_SMALL")
        bankline_wizard.input_name = "WORKING_SAMPLE_SMALL"  # Usually handled in GUI
        cls.wizard_rec = bankline_wizard.save()
        cls.wizard_rec.import_bankline_file()
        cls.created_bankstatement = cls.bankstatement_obj.search(
            [("created_via_bankline_import", "=", True)]
        )

    def test_audit_log_values(self):
        audit_log = self.env["account.bankline.import.log"].search([])
        self.assertEqual(len(audit_log), 1)
        self.assertEqual(audit_log.name, "WORKING_SAMPLE_SMALL")
        self.assertEqual(audit_log.bankline_row_count, 1)

    def test_bankstatement_values(self):
        self.assertEqual(self.created_bankstatement.journal_id, self.created_journal)

    def test_bankstatement_line_values(self):
        self.assertAlmostEqual(self.created_bankstatement.line_ids[0].amount, -113.9)
