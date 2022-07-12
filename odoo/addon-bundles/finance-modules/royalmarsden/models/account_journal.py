from psycopg2.extensions import AsIs

from odoo import api, fields, models
from odoo.tools.misc import formatLang


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.model
    def configure_payment_methods_on_bank_journals(self):
        # Called from data xml, as bank journal has no extid
        # On every upgrade we will want all journals of type bank
        # to have these outgoing payment methods configured
        bank_journals = self.search([("type", "=", "bank")])
        bacs_out_payment_method = self.env.ref(
            "royalmarsden.account_payment_method_bacs_out"
        )
        nonbacs_out_payment_method = self.env.ref(
            "royalmarsden.account_payment_method_nonbacs_out"
        )
        for bank_journal in bank_journals:
            bank_journal.write(
                dict(outbound_payment_method_ids=[[4, bacs_out_payment_method.id]])
            )
            bank_journal.write(
                dict(outbound_payment_method_ids=[[4, nonbacs_out_payment_method.id]])
            )

    def get_journal_dashboard_datas(self):
        """
        If General Ledger dashboard tile is 'Bank' then it should not include the
        'Year End' journal in the sum.

        The bank journal and year end journal do not have xml ids, so a search has to
        be used.
        """
        res = super(AccountJournal, self).get_journal_dashboard_datas()
        currency = self.currency_id or self.company_id.currency_id
        bank_journal = self.search([("name", "=", "Bank")])
        year_end_journal = self.search([("name", "=", "YE JNRL")])
        account_ids = tuple(
            ac
            for ac in [
                self.default_debit_account_id.id,
                self.default_credit_account_id.id,
            ]
            if ac
        )
        if account_ids and self == bank_journal:
            amount_field = (
                "aml.balance"
                if (
                    not self.currency_id
                    or self.currency_id == self.company_id.currency_id
                )
                else "aml.amount_currency"
            )
            query = """
                SELECT sum(%(amount_field)s) FROM account_move_line aml
                LEFT JOIN account_move move ON aml.move_id = move.id
                WHERE aml.account_id in %(account_ids)s
                AND move.date <= %(date)s AND move.state = 'posted'
                AND aml.journal_id != %(journal_id)s;
            """
            self.env.cr.execute(
                query,
                {
                    "amount_field": AsIs(amount_field),
                    "account_ids": account_ids,
                    "date": fields.Date.context_today(self),
                    "journal_id": year_end_journal.id,
                },
            )
            query_result_balance_gl = self.env.cr.dictfetchall()
            if (
                query_result_balance_gl
                and query_result_balance_gl[0].get("sum") is not None
            ):
                account_sum = query_result_balance_gl[0].get("sum")
                res["account_balance"] = formatLang(
                    self.env, currency.round(account_sum) + 0.0, currency_obj=currency
                )

        return res
