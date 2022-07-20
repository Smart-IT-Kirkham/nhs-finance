import base64
import csv
import datetime
import secrets
from io import StringIO

from odoo import SUPERUSER_ID, _, fields, models
from odoo.exceptions import AccessError, ValidationError

EXPECTED_COLUMN_COUNTS = {
    "FH": 4,
    "IH": 13,
    "TL": 13,
    "IF": 3,
}

ROW_TYPE_MAPPING = {
    "STANDARD": "in_invoice",
    "CREDIT": "in_refund",
}


class AccountJacImportLog(models.Model):
    _name = "account.jac.import.log"
    _description = "JAC Import Log for Audit purposes"

    name = fields.Char(string="JAC File Name", readonly=True)
    date_of_import = fields.Datetime(string="Date and time", readonly=True)
    jac_header_row_count = fields.Float(string="JAC header rows", readonly=True)
    jac_line_row_count = fields.Float(string="JAC lines rows", readonly=True)
    jac_header_total = fields.Float(string="JAC header total", readonly=True)
    jac_lines_total = fields.Float(string="JAC lines total", readonly=True)
    user_id = fields.Many2one("res.users", string="Imported By", readonly=True)


class AccountJacImport(models.TransientModel):
    _name = "account.jac.import"
    _description = "JAC Import"

    input_file = fields.Binary()
    input_name = fields.Char(string="File Name")

    def _freight_product(self):
        """
        @returns: product.product recordset for SKU FREIGHT. Can be empty
        """
        return self.env["product.product"].search([("default_code", "=", "FREIGHT")])

    def _drugs_product(self):
        """
        @returns: product.product recordset for SKU DRUGS. Can be empty
        """
        return self.env["product.product"].search([("default_code", "=", "DRUGS")])

    def evaluate_seen_taxes(self, seen_tax_names, EXCEPTION_MESSAGE):
        for seen_tax_name in set(seen_tax_names):
            if not self.env["account.tax"].search(
                [("jac_import_tax_name", "=", seen_tax_name)]
            ):
                EXCEPTION_MESSAGE += (
                    "Could not find tax with "
                    "JAC Import Oracle vat code name {} "
                    "in the system\n".format(seen_tax_name)
                )
        return EXCEPTION_MESSAGE

    def evaluate_seen_payment_terms(self, seen_payment_term_names, EXCEPTION_MESSAGE):
        for seen_payment_term in set(seen_payment_term_names):
            if not self.env["account.payment.term"].search(
                [("jac_import_payment_term_name", "=", seen_payment_term)]
            ):
                EXCEPTION_MESSAGE += (
                    "Could not find payment term with "
                    "JAC Import payment term name {} "
                    "in the system\n".format(seen_payment_term)
                )
        return EXCEPTION_MESSAGE

    def evaluate_seen_prices(
        self,
        seen_line_amounts,
        seen_line_unit_prices,
        seen_discount_amounts,
        seen_ih_amounts,
        EXCEPTION_MESSAGE,
    ):
        for seen_line_amount in seen_line_amounts:
            try:
                float(seen_line_amount)
            except Exception:
                EXCEPTION_MESSAGE += (
                    "Could not determine a Float value "
                    "for Line amount: {}\n".format(seen_line_amount)
                )
        for seen_line_unit_price in seen_line_unit_prices:
            try:
                float(seen_line_unit_price)
            except Exception:
                EXCEPTION_MESSAGE += (
                    "Could not determine a Float value "
                    "for Unit price: {}\n".format(seen_line_unit_price)
                )
        for seen_discount_amount in seen_discount_amounts:
            try:
                float(seen_discount_amount)
            except Exception:
                EXCEPTION_MESSAGE += (
                    "Could not determine a Float value "
                    "for Amount of invoice applicable to discount: {}\n".format(
                        seen_discount_amount
                    )
                )
        for seen_ih_amount in seen_ih_amounts:
            try:
                float(seen_ih_amount)
            except Exception:
                EXCEPTION_MESSAGE += (
                    "Could not determine a Float value "
                    "for IH amount: {}\n".format(seen_ih_amount)
                )
        return EXCEPTION_MESSAGE

    def evaluate_seen_lookup_codes(self, seen_lookup_codes, EXCEPTION_MESSAGE):
        non_standard_or_credit_codes = [
            code for code in seen_lookup_codes if code not in ["STANDARD", "CREDIT"]
        ]
        if non_standard_or_credit_codes:
            EXCEPTION_MESSAGE += (
                "The following Invoice Type Lookup Codes are invalid "
                "{}\n".format(non_standard_or_credit_codes)
            )
        return EXCEPTION_MESSAGE

    def evaluate_seen_accounting_dates(self, seen_accounting_dates, EXCEPTION_MESSAGE):
        closed_or_not_created_periods = [
            period_date
            for period_date in seen_accounting_dates
            if not self.env["account.period"].search(
                [
                    ("state", "!=", "done"),
                    ("special", "=", False),
                    ("date_start", "<=", period_date),
                    ("date_stop", ">=", period_date),
                    ("company_id", "=", self.env.user.company_id.id),
                ],
                limit=1,
            )
        ]
        if closed_or_not_created_periods:
            EXCEPTION_MESSAGE += (
                "The following Dates do not belong to open periods "
                "{}\n".format(closed_or_not_created_periods)
            )
        return EXCEPTION_MESSAGE

    def evaluate_row_count(
        self, row, rowcount, row_type, row_expected_column_count, EXCEPTION_MESSAGE
    ):
        actual_column_count = len([v for k, v in row.items() if v is not None])
        if actual_column_count != row_expected_column_count:
            EXCEPTION_MESSAGE += (
                "Row {} did not have the expected amount "
                "of columns for a row of type {}\n".format(rowcount, row_type)
            )
        return EXCEPTION_MESSAGE

    def evaluate_seen_suppliers(
        self, seen_supplier_identifiers, suppliers_cache, EXCEPTION_MESSAGE
    ):
        for supplier_identifier in set(seen_supplier_identifiers):
            existing_supplier = suppliers_cache.filtered(
                lambda supplier: supplier.jac_vsr_number == supplier_identifier
            )
            if not existing_supplier:
                EXCEPTION_MESSAGE += (
                    "Could not find supplier with JAC VSR Identifier {} "
                    "in the system\n".format(supplier_identifier)
                )
        return EXCEPTION_MESSAGE

    def evaluate_seen_invoices(
        self, seen_move_identifiers, existing_moves_with_ref, EXCEPTION_MESSAGE
    ):
        for seen_move in set(seen_move_identifiers):
            pre_existing_move = existing_moves_with_ref.filtered(
                lambda move: move.ref == seen_move
            )
            if pre_existing_move:
                EXCEPTION_MESSAGE += (
                    "Duplicate invoice found in the system. "
                    "Invoice identifier: {}\n".format(seen_move)
                )
        return EXCEPTION_MESSAGE

    def evaluate_seen_accounts(
        self, seen_account_codes, accounts_cache, EXCEPTION_MESSAGE
    ):
        for unqiue_account in set(seen_account_codes):
            existing_account = accounts_cache.filtered(
                lambda account: account.code == unqiue_account
            )
            if not existing_account:
                EXCEPTION_MESSAGE += (
                    "Could not find account with code {} "
                    "in the Odoo system\n".format(unqiue_account)
                )
        return EXCEPTION_MESSAGE

    def evaluate_flags(self, seen_row_flags, EXCEPTION_MESSAGE):
        not_found_rows_of_type = [k for k, v in seen_row_flags.items() if v is False]
        if not_found_rows_of_type:
            EXCEPTION_MESSAGE += (
                "The JAC file must contain at least all four "
                "types of row (FH, IH, TL, IF). Missing types in this file"
                "include {}\n".format(not_found_rows_of_type)
            )
        return EXCEPTION_MESSAGE

    def preflight_checks(
        self, accounts_cache, suppliers_cache, existing_moves_with_ref
    ):
        """
        @returns <dict> of stats gathered from jac file. Used for log model
        @param accounts_cache: account.account recordsets
        @param suppliers_cache: res.partner recordsets
        @param existing_moves_with_ref: account.move recordsets

        Ensure the input file conforms to the expected file spec.

        If there are any failures, an exception will be raised to the user
        and the import will not go ahead.
        """

        reader = self.csvreader_for_input_file()
        EXCEPTION_MESSAGE = ""
        seen_row_flags = {
            "FH": False,
            "IH": False,
            "TL": False,
            "IF": False,
        }
        seen_account_codes = []
        seen_move_identifiers = []
        seen_supplier_identifiers = []
        seen_lookup_codes = []
        seen_ih_amounts = []
        seen_line_amounts = []
        seen_line_unit_prices = []
        seen_payment_term_names = []
        seen_discount_amounts = []
        seen_tax_names = []
        seen_accounting_dates = []
        jac_file_stats = {
            "iheader_count": 0.0,
            "tline_count": 0.0,
            "iheader_total": 0.0,
            "tline_total": 0.0,
        }
        # Loop over the a subset of the file contents and validate all looks OK
        # pushing errors to a string which is raised at the end (if any)
        for rowcount, row in enumerate(reader):
            # Get row identifier, and move to next row if it is invalid
            row_type = row.get("1")
            try:
                row_expected_column_count = EXPECTED_COLUMN_COUNTS[row_type]
                seen_row_flags[row_type] = True
            except KeyError:
                EXCEPTION_MESSAGE += (
                    "First column of row {} started with {}. "
                    "Expected one of [FH,IH,TL,IF]\n".format(rowcount, row_type)
                )
                continue
            EXCEPTION_MESSAGE = self.evaluate_row_count(
                row, rowcount, row_type, row_expected_column_count, EXCEPTION_MESSAGE
            )
            # Row type specific checks
            if row_type == "IH":
                jac_file_stats["iheader_count"] += 1
                seen_ih_amounts.append(row.get("10"))
                seen_move_identifiers.append(row.get("5"))
                seen_supplier_identifiers.append(row.get("9"))
                seen_lookup_codes.append(row.get("6"))
                if (
                    datetime.datetime.strptime(row.get("12"), "%d-%b-%y")
                    not in seen_accounting_dates
                ):
                    seen_accounting_dates.append(
                        datetime.datetime.strptime(row.get("12"), "%d-%b-%y")
                    )
                seen_payment_term_names.append(row.get("11"))
                seen_discount_amounts.append(row.get("13"))
            elif row_type == "TL":
                jac_file_stats["tline_count"] += 1
                seen_tax_names.append(row.get("12"))
                seen_account_codes.append(row.get("4"))
                seen_line_amounts.append(row.get("10"))
                seen_line_unit_prices.append(row.get("11"))
        if not self.env["account.journal"].search(
            [("name", "=", "Vendor Bills")], limit=1
        ):
            EXCEPTION_MESSAGE += (
                "Could not find Journal with name 'Vendor Bills' in the system\n"
            )
        if not self._drugs_product():
            EXCEPTION_MESSAGE += (
                "Could not find product with SKU 'DRUGS' in the system\n"
            )
        if not self._freight_product():
            EXCEPTION_MESSAGE += (
                "Could not find product with SKU 'FREIGHT' in the system\n"
            )
        if self.env["account.jac.import.log"].search([("name", "=", self.input_name)]):
            EXCEPTION_MESSAGE += (
                "You have previously tried to import a file"
                "with this name: {}\n".format(self.input_name)
            )
        EXCEPTION_MESSAGE = self.evaluate_seen_taxes(seen_tax_names, EXCEPTION_MESSAGE)
        EXCEPTION_MESSAGE = self.evaluate_seen_payment_terms(
            seen_payment_term_names, EXCEPTION_MESSAGE
        )
        EXCEPTION_MESSAGE = self.evaluate_seen_prices(
            seen_line_amounts,
            seen_line_unit_prices,
            seen_discount_amounts,
            seen_ih_amounts,
            EXCEPTION_MESSAGE,
        )
        EXCEPTION_MESSAGE = self.evaluate_seen_lookup_codes(
            seen_lookup_codes, EXCEPTION_MESSAGE
        )
        EXCEPTION_MESSAGE = self.evaluate_seen_accounting_dates(
            seen_accounting_dates, EXCEPTION_MESSAGE
        )
        EXCEPTION_MESSAGE = self.evaluate_seen_suppliers(
            seen_supplier_identifiers, suppliers_cache, EXCEPTION_MESSAGE
        )
        EXCEPTION_MESSAGE = self.evaluate_seen_invoices(
            seen_move_identifiers, existing_moves_with_ref, EXCEPTION_MESSAGE
        )
        EXCEPTION_MESSAGE = self.evaluate_seen_accounts(
            seen_account_codes, accounts_cache, EXCEPTION_MESSAGE
        )
        EXCEPTION_MESSAGE = self.evaluate_flags(seen_row_flags, EXCEPTION_MESSAGE)
        try:
            jac_file_stats["iheader_total"] = sum([float(x) for x in seen_ih_amounts])
            jac_file_stats["tline_total"] = sum([float(x) for x in seen_line_amounts])
        except ValueError:
            # If any are invalid floats, we don't care as jac_file_stats won't ever get
            # written to the log, and their exceptions are handled in
            # evaluate_seen_prices anyway
            pass
        if EXCEPTION_MESSAGE:
            raise ValidationError(_(EXCEPTION_MESSAGE))
        return jac_file_stats

    def import_file(self, accounts_cache, suppliers_cache):
        """
        @param accounts_cache: account.account recordsets
        @param suppliers_cache: res.partner recordsets

        Imports the file, assuming all data is present in the cache,
        and the only exceptions will be ones outside of our control,
        which we will let Odoo handle as to roll back if any exceptions are hit
        """

        def import_move():
            row_prime_key = row.get("4")
            row_inv_ref = row.get("5")
            row_type = row.get("6")
            row_bill_date = row.get("7")
            # TODO: Awaiting clarification from NG on how row_trans_desc should be used
            #         Will be tackled as part of another task (out of scope of O2521)
            # row_trans_desc = row.get("8")
            row_supplier_vsr = row.get("9")
            row_payment_term = row.get("11")
            row_accounting_date = row.get("12")
            row_discount_amount = float(row.get("13"))

            supplier = suppliers_cache.filtered(
                lambda supplier: supplier.jac_vsr_number == row_supplier_vsr
            )
            bill_date = datetime.datetime.strptime(row_bill_date, "%d-%b-%y")
            accounting_date = datetime.datetime.strptime(
                row_accounting_date, "%d-%b-%y"
            )
            payment_term_id = (
                self.env["account.payment.term"]
                .search(
                    [("jac_import_payment_term_name", "=", row_payment_term)], limit=1
                )
                .id
            )

            return move_obj.create(
                dict(
                    invoice_payment_term_id=payment_term_id,
                    created_via_jac_import=True,
                    jac_prime_key=row_prime_key,
                    jac_import_token=import_token,
                    ref=row_inv_ref,
                    type=ROW_TYPE_MAPPING[row_type],
                    date=accounting_date,
                    invoice_date=bill_date,
                    # TODO: This will be changed at a later date
                    journal_id=self.env["account.journal"]
                    .search([("name", "=", "Vendor Bills")], limit=1)
                    .id,
                    partner_id=supplier.id,
                    jac_discount_amount=row_discount_amount,
                )
            )

        def import_line():
            row_move_prime_key = row.get("2")
            row_account_code = row.get("4")
            row_item_name = row.get("8")
            row_item_type = row.get("9")
            # Use abs as when RM provide a CREDIT type file the values are negative
            # but Odoo needs positive values,
            # and we just switch the invoice type to in_refund
            row_line_amount = abs(float(row.get("10")))
            row_oracle_vatcode = row.get("12")

            tax = self.env["account.tax"].search(
                [("jac_import_tax_name", "=", row_oracle_vatcode)], limit=1
            )
            item_product_id = self._drugs_product()
            freight_product_id = self._freight_product()
            account = accounts_cache.filtered(
                lambda account: account.code == row_account_code
            )
            move = move_obj.search(
                [
                    ("created_via_jac_import", "=", True),
                    ("jac_prime_key", "=", row_move_prime_key),
                    ("jac_import_token", "=", import_token),
                ]
            )
            if (
                row_item_type == "TAX"
            ):  # Ignore tax lines as Odoo handles tax on its own
                return

            invoice_line_vals = []

            # When writing the new line, the old lines have their names recomputed.
            # Add the existing lines to the list to write their names again.
            for line in move.invoice_line_ids:
                invoice_line_vals.append(
                    (
                        1,
                        line.id,
                        {
                            "name": line.name,
                        },
                    )
                )

            invoice_line_vals.append(
                (
                    0,
                    False,
                    {
                        "product_id": item_product_id.id
                        if row_item_type == "ITEM"
                        else freight_product_id.id,
                        "name": row_item_name,
                        "account_id": account.id,
                        "quantity": 1.0,
                        "price_unit": row_line_amount,
                        "tax_ids": [(6, False, [tax.id])],
                    },
                )
            )

            move.write({"invoice_line_ids": invoice_line_vals})

        reader = self.csvreader_for_input_file()
        import_token = secrets.token_hex(16)
        move_obj = self.env["account.move"]
        created_moves = move_obj
        for row in reader:
            row_type = row.get("1")  # Will always be valid if we have gotten this far
            if row_type == "IH":
                created_moves |= import_move()
            elif row_type == "TL":
                import_line()
        return created_moves

    def csvreader_for_input_file(self):
        """
        @returns <DictReader>

        As the input file has variable column counts per row, we need
        to spoof the csv DictReader to have a column count that is the same
        as the maximum amount of expected columns.

        If there is a row with less than this max column count, then
        csv.DictReader will still have keys beyond the columns for that
        row, but the values will be None
        """
        input_string = base64.b64decode(self.input_file).decode("utf-8")
        pseudo_file = StringIO(input_string)
        max_column_count = max([v for k, v in EXPECTED_COLUMN_COUNTS.items()])
        # Use +1 as we want indexing to start at 1 for ease of readability when
        # checking against the reference doc (which refs col numbers starting at 1)
        reader = csv.DictReader(
            pseudo_file, fieldnames=[str(x + 1) for x in range(max_column_count)]
        )
        return reader

    def import_jac_file(self):
        """
        @returns <odoo action>

        Main function called from wizard button for JAC Import which takes
        an arbitrary input file and verifies its contents before importing
        into Odoo as account.move and account.move.line recordsets
        """
        # Explicitly prevent non account managers (or superuser) from running any
        # of the following code, as transientmodels do not have access rules.
        # Without this, it should fail further down the line anyway, but I would
        # rather have a sane looking error for this situation
        if not self.env.su and not self.env.user.has_group(
            "account.group_account_invoice"
        ):
            raise AccessError(_("You don't have access rights to perform a JAC Import"))
        # Bring cache in once, passing to both preflight and import
        # to save on unnecessary db calls
        user = self.env.user
        self = self.with_user(SUPERUSER_ID)
        accounts_cache = self.env["account.account"].search([])
        suppliers_cache = self.env["res.partner"].search([("supplier_rank", ">", 0)])
        existing_moves_with_ref = self.env["account.move"].search(
            [("ref", "!=", False)]
        )
        jac_file_stats = self.preflight_checks(
            accounts_cache, suppliers_cache, existing_moves_with_ref
        )
        created_moves = self.import_file(accounts_cache, suppliers_cache)
        for move in created_moves:
            move.discount_amount = move.jac_discount_amount
            move.discount_method = "fix" if move.jac_discount_amount else False
            move.action_post()
        # Create a log item for audit purposes
        self.env["account.jac.import.log"].create(
            dict(
                name=self.input_name,
                date_of_import=datetime.datetime.now(),
                jac_header_row_count=jac_file_stats["iheader_count"],
                jac_line_row_count=jac_file_stats["tline_count"],
                jac_header_total=jac_file_stats["iheader_total"],
                jac_lines_total=jac_file_stats["tline_total"],
                user_id=user.id,
            )
        )
        # Redirect the user to the newly created vendor bills
        tree_view_id = self.env.ref("account.view_move_tree").id
        form_view_id = self.env.ref("account.view_move_form").id
        return {
            "name": "Imported the following bills",
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "views": [(tree_view_id, "tree"), (form_view_id, "form")],
            "view_id": tree_view_id,
            "view_mode": "tree,form",
            "domain": [("id", "in", created_moves.ids)],
            "target": "self",
            "context": {"default_type": "in_invoice"},
        }
