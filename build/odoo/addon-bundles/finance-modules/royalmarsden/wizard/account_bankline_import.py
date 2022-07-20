import base64
import csv
import datetime
from io import StringIO

from odoo import SUPERUSER_ID, _, fields, models
from odoo.exceptions import AccessError, ValidationError

EXPECTED_COLUMN_COUNT = 18


class AccountBanklineImportLog(models.Model):
    _name = "account.bankline.import.log"
    _description = "Bankline Import Log for Audit purposes"

    name = fields.Char(string="Bankline File Name", readonly=True)
    date_of_import = fields.Datetime(string="Date and time", readonly=True)
    bankline_row_count = fields.Integer(string="Bankline rows", readonly=True)


class AccountBanklineImport(models.TransientModel):
    _name = "account.bankline.import"
    _description = "Bankline Import"

    input_file = fields.Binary()
    input_name = fields.Char(string="File Name")

    def evaluate_seen_account_details(
        self,
        seen_account_details,
        res_partner_bank_cache,
        res_bank_cache,
        journals_cache,
        EXCEPTION_MESSAGE,
    ):
        if not all(x == seen_account_details[0] for x in seen_account_details):
            EXCEPTION_MESSAGE += (
                "All rows account details must be identical for a given import\n"
            )
        for account_dict in seen_account_details:
            existing_journal = self._journal_for_row_account_data_dict(
                account_dict, res_partner_bank_cache, res_bank_cache, journals_cache
            )
            if not existing_journal:
                EXCEPTION_MESSAGE += (
                    "Could not find journal in the system who has a Bank Account"
                    "with values: \n"
                    + self._informative_account_dict_string(account_dict)
                )
            if len(existing_journal) > 1:
                EXCEPTION_MESSAGE += (
                    "Found > 1 journal in the system who has a Bank Account"
                    "with values: \n"
                    + self._informative_account_dict_string(account_dict)
                )
        return EXCEPTION_MESSAGE

    def evaluate_seen_type_details(
        self, seen_type_names, statement_types_cache, EXCEPTION_MESSAGE
    ):
        for type_name in set(seen_type_names):
            existing_type = statement_types_cache.filtered(
                lambda statement_type: statement_type.name == type_name
            )
            if not existing_type:
                EXCEPTION_MESSAGE += (
                    "Could not find bank statement type with name {}\n".format(
                        type_name
                    )
                )
        return EXCEPTION_MESSAGE

    def evaluate_dr_cr_floats(self, seen_debits, seen_credits, EXCEPTION_MESSAGE):
        for debit in seen_debits:
            if debit:
                try:
                    float(debit)
                except (TypeError, ValueError):
                    EXCEPTION_MESSAGE += (
                        "Could not evaluate a float value for"
                        "debit from {}\n".format(debit)
                    )
        for credit in seen_credits:
            if credit:
                try:
                    float(credit)
                except (TypeError, ValueError):
                    EXCEPTION_MESSAGE += (
                        "Could not evaluate a float value for"
                        "credit from {}\n".format(credit)
                    )
        return EXCEPTION_MESSAGE

    def evaluate_seen_line_dates(self, seen_line_dates, EXCEPTION_MESSAGE):
        for line_date in seen_line_dates:
            if line_date:
                try:
                    line_date = datetime.datetime.strptime(line_date, "%d/%m/%Y")
                except (TypeError, ValueError):
                    EXCEPTION_MESSAGE += (
                        "Could not evaluate a date value from {}\n".format(line_date)
                    )
        return EXCEPTION_MESSAGE

    def preflight_checks(
        self,
        journals_cache,
        res_partner_bank_cache,
        res_bank_cache,
        statement_types_cache,
    ):
        """
        @returns: <dict> of stats gathered from bankline file. Used for log model
        @param journals_cache: account.journal recordsets

        Ensure the input file conforms to the expected file spec.

        If there are any failures, an exception will be raised to the user
        and the import will not go ahead.
        """
        reader = self.csvreader_for_input_file()
        EXCEPTION_MESSAGE = ""
        bankline_file_stats = {
            "bankline_count": 0,
        }
        seen_account_details = []
        seen_type_names = []
        seen_debits = []
        seen_credits = []
        seen_line_dates = []
        for rowcount, row in enumerate(reader):
            if len([x for x in row if row.get(x) is not None]) != EXPECTED_COLUMN_COUNT:
                EXCEPTION_MESSAGE += (
                    "Row {} Did not contain the expected"
                    "amount of columns ({})\n".format(
                        rowcount + 1,
                        EXPECTED_COLUMN_COUNT,  # +1 to account for header
                    )
                )
                continue
            seen_account_details.append(self._row_account_data_dict(row))
            seen_debits.append(row.get("Debit"))
            seen_credits.append(row.get("Credit"))
            row.get("Type") and seen_type_names.append(row.get("Type"))
            seen_line_dates.append(row.get("Date"))
            bankline_file_stats["bankline_count"] += 1
        if self.env["account.bankline.import.log"].search(
            [("name", "=", self.input_name)]
        ):
            EXCEPTION_MESSAGE += (
                "You have previously tried to import a file"
                "with this name: {}\n".format(self.input_name)
            )
        EXCEPTION_MESSAGE = self.evaluate_seen_account_details(
            seen_account_details,
            res_partner_bank_cache,
            res_bank_cache,
            journals_cache,
            EXCEPTION_MESSAGE,
        )
        EXCEPTION_MESSAGE = self.evaluate_seen_type_details(
            seen_type_names, statement_types_cache, EXCEPTION_MESSAGE
        )
        EXCEPTION_MESSAGE = self.evaluate_dr_cr_floats(
            seen_debits, seen_credits, EXCEPTION_MESSAGE
        )
        EXCEPTION_MESSAGE = self.evaluate_seen_line_dates(
            seen_line_dates, EXCEPTION_MESSAGE
        )

        if EXCEPTION_MESSAGE:
            raise ValidationError(_(EXCEPTION_MESSAGE))
        return bankline_file_stats

    def _informative_account_dict_string(self, account_dict):
        """
        @returns <str>
        @param account_dict: result of _row_account_data_dict()

        Called when building an exception message. The account details
        are long winded and intricate and called more than once, hence being a function
        """
        return (
            "  Account number: {}\n"
            "  Sort Code: {}\n"
            "  Account Holder Name: {}\n"
            "  Short Name: {}\n"
            "  Account Type: {}\n"
            "and a Bank with values: \n"
            "  Bank Identifier Code: {}\n"
            "  Name: {}\n"
            "  Branch Name: {}\n".format(
                account_dict["account_number"],
                account_dict["sort_code"],
                account_dict["account_alias"],
                account_dict["account_short_name"],
                account_dict["account_type"],
                account_dict["bic"],
                account_dict["bank_name"],
                account_dict["branch_name"],
            )
        )

    def _journal_for_row_account_data_dict(
        self, account_dict, res_partner_bank_cache, res_bank_cache, journals_cache
    ):
        """
        @returns <account.journal> recordset, can be empty
        @param account_dict: result of _row_account_data_dict()
        @param res_partner_bank_cache: <res.partner.bank> recordsets to filter
        @param res_bank_cache: <res.bank> recordsets to filter
        @param journals_cache: <account.journal> recordsets to filter

        Returns a journal in the system based on the data provided in account_data_dict
        using the cached objs
        (they will generally just be a full .search([]) on the models)
        """
        existing_partner_bank = res_partner_bank_cache.filtered(
            lambda partner_bank: partner_bank.acc_number
            == account_dict.get("account_number")
            and partner_bank.sort_code == account_dict.get("sort_code")
            and partner_bank.acc_holder_name == account_dict.get("account_alias")
            and partner_bank.short_name == account_dict.get("account_short_name")
            and partner_bank.account_type.name == account_dict.get("account_type")
        )
        existing_bank = res_bank_cache.filtered(
            lambda bank: bank.bic == account_dict.get("bic")
            and bank.name == account_dict.get("bank_name")
            and bank.branch_name == account_dict.get("branch_name")
        )
        existing_journal = journals_cache.filtered(
            lambda journal: journal.bank_account_id == existing_partner_bank
            and journal.bank_id == existing_bank
        )
        return existing_journal

    def _row_account_data_dict(self, row):
        """
        @returns <dict> of account information mapped from row
        @param row: OrderedDict
        """
        return dict(
            sort_code=row.get("Sort Code"),
            account_number=row.get("Account Number"),
            account_alias=row.get("Account Alias"),
            account_short_name=row.get("Account Short Name"),
            account_type=row.get("Account Type"),
            bic=row.get("BIC"),
            bank_name=row.get("Bank Name"),
            branch_name=row.get("Branch Name"),
        )

    def import_file(
        self,
        journals_cache,
        res_partner_bank_cache,
        res_bank_cache,
        statement_types_cache,
    ):
        """
        @param journals_cache: account.journal recordsets

        Imports the file, assuming all data is present in the cache,
        and the only exceptions will be ones outside of our control,
        which we will let Odoo handle as to roll back if any exceptions are hit
        """
        reader = self.csvreader_for_input_file()
        bank_statement_obj = self.env["account.bank.statement"]
        created_statement = bank_statement_obj
        for row in reader:
            # For a given import, each row represents an account.bank.statement.line
            # connected to a single new account.bank.statement record. It relies on row
            # data to create, hence is created within the loop
            if not created_statement:
                account_details = self._row_account_data_dict(row)
                journal = self._journal_for_row_account_data_dict(
                    account_details,
                    res_partner_bank_cache,
                    res_bank_cache,
                    journals_cache,
                )
                created_statement |= bank_statement_obj.create(
                    dict(
                        journal_id=journal.id,
                        date=datetime.datetime.today(),
                        created_via_bankline_import=True,
                        name=self.input_name,
                    )
                )
            existing_type = (
                row.get("Type")
                and statement_types_cache.filtered(
                    lambda statement_type: statement_type.name == row.get("Type")
                )
                or False
            )
            debit = row.get("Debit")
            credit = row.get("Credit")
            amount = 0.0
            partner_id = False
            # Values in the sheet are already marked as positive / negative
            # and are ignored if left blank (will result in None)
            if debit:
                amount = float(debit)
            if credit:
                amount = float(credit)
            narrative_one = row.get("Narrative #1")
            if narrative_one:
                partners = self.env["res.partner"].search(
                    [("supplier_rank", ">", 0), ("name", "=", narrative_one)]
                )
                # Needs to discuss with Narender that in case that are more
                # than one partner with the same code what should be done
                partner_id = partners[0].id if len(partners) == 1 else False
            narrative_two = row.get("Narrative #2")
            narrative_three = row.get("Narrative #3")
            narrative_four = row.get("Narrative #4")
            narrative_five = row.get("Narrative #5")
            line_date = datetime.datetime.strptime(row.get("Date"), "%d/%m/%Y")
            self.env["account.bank.statement.line"].create(
                dict(
                    name=row.get("Narrative #3") or "N/A",
                    date=line_date,
                    amount=amount,
                    partner_id=partner_id,
                    statement_id=created_statement.id,
                    narrative_one=narrative_one,
                    narrative_two=narrative_two,
                    narrative_three=narrative_three,
                    narrative_four=narrative_four,
                    narrative_five=narrative_five,
                    line_type_id=existing_type and existing_type.id or False,
                )
            )
        return created_statement

    def csvreader_for_input_file(self):
        """
        @returns <DictReader>

        A nice k,v pair for each header/value, for reach row
        """
        input_string = base64.b64decode(self.input_file).decode("utf-8")
        pseudo_file = StringIO(input_string)
        reader = csv.DictReader(pseudo_file)
        return reader

    def check_import_bankline_right(self):
        if not self.env.su and (
            not self.env.user.has_group("account.group_account_manager")
            or not self.env.user.has_group("account.group_account_user")
        ):
            raise AccessError(
                _(
                    "You don't have access rights to perform a Bankline Import. "
                    "You must be an 'Account Manager' and "
                    "have 'Show Full Accounting Features' enabled"
                )
            )

    def import_bankline_file(self):
        """
        @returns <odoo action>

        Main function called from wizard button for Bankline Import which takes
        an arbitrary input file and verifies its contents before importing
        into Odoo as account.bank.statement and account.bank.statement.line rows.
        View it under Invoicing --> Overview --> Bank Journal
        """
        # Explicitly prevent non account managers (or superuser) from running any
        # of the following code, as transientmodels do not have access rules.
        # Without this, it should fail further down the line anyway, but I would
        # rather have a sane looking error for this situation
        self.check_import_bankline_right()
        # Bring cache in once, passing to both preflight and import
        # to save on unnecessary db calls
        journals_cache = self.env["account.journal"].search([])
        res_partner_bank_cache = self.env["res.partner.bank"].search([])
        res_bank_cache = self.env["res.bank"].search([])
        statement_types_cache = self.env["bank.statement.line.type"].search([])
        bankline_file_stats = self.preflight_checks(
            journals_cache,
            res_partner_bank_cache,
            res_bank_cache,
            statement_types_cache,
        )
        created_statement = self.import_file(
            journals_cache,
            res_partner_bank_cache,
            res_bank_cache,
            statement_types_cache,
        )
        # Create a log item for audit purposes
        self.env["account.bankline.import.log"].with_user(SUPERUSER_ID).create(
            dict(
                name=self.input_name,
                date_of_import=datetime.datetime.now(),
                bankline_row_count=bankline_file_stats["bankline_count"],
            )
        )
        # Redirect the user to the newly created bank statement
        form_view_id = self.env.ref("account.view_bank_statement_form").id
        tree_view_id = self.env.ref("account.view_bank_statement_tree").id
        return {
            "name": "Imported the following statement",
            "type": "ir.actions.act_window",
            "res_model": "account.bank.statement",
            "views": [(tree_view_id, "tree"), (form_view_id, "form")],
            "view_id": tree_view_id,
            "view_mode": "tree,form",
            "domain": [("id", "in", created_statement.ids)],
            "context": {"journal_type": "bank"},
            "target": "self",
        }
