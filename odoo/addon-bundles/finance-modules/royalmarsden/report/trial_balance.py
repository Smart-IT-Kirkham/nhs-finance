import logging
from datetime import timedelta

from odoo import api, models
from odoo.tools import date_utils
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT

_LOGGER = logging.getLogger(__name__)


class TrialBalanceReport(models.AbstractModel):
    _inherit = "report.account_financial_report.trial_balance"

    # _get_data copied from
    # .../OCA_account-financial-reporting/account_financial_report/report/trial_balance.py
    # See git blame and the git history of this region to find out what we changed
    @api.model
    def _get_data(
        self,
        account_ids,
        journal_ids,
        partner_ids,
        company_id,
        date_to,
        date_from,
        foreign_currency,
        only_posted_moves,
        show_partner_details,
        hide_account_at_0,
        unaffected_earnings_account,
        fy_start_date,
    ):
        accounts_domain = [("company_id", "=", company_id)]
        if account_ids:
            accounts_domain += [("id", "in", account_ids)]
        accounts = self.env["account.account"].search(accounts_domain)
        tb_initial_acc = []
        for account in accounts:
            tb_initial_acc.append(
                {"account_id": account.id, "balance": 0.0, "amount_currency": 0.0}
            )
        initial_domain_bs = self._get_initial_balances_bs_ml_domain(
            account_ids,
            journal_ids,
            partner_ids,
            company_id,
            date_from,
            only_posted_moves,
            show_partner_details,
        )
        tb_initial_acc_bs = self.env["account.move.line"].read_group(
            domain=initial_domain_bs,
            fields=["account_id", "balance", "amount_currency"],
            groupby=["account_id"],
        )
        initial_domain_pl = self._get_initial_balances_pl_ml_domain(
            account_ids,
            journal_ids,
            partner_ids,
            company_id,
            date_from,
            only_posted_moves,
            show_partner_details,
            fy_start_date,
        )
        tb_initial_acc_pl = self.env["account.move.line"].read_group(
            domain=initial_domain_pl,
            fields=["account_id", "balance", "amount_currency"],
            groupby=["account_id"],
        )
        tb_initial_acc_rg = tb_initial_acc_bs + tb_initial_acc_pl
        for account_rg in tb_initial_acc_rg:
            element = list(
                filter(
                    lambda acc_dict: acc_dict["account_id"]
                    == account_rg["account_id"][0],
                    tb_initial_acc,
                )
            )
            if element:
                element[0]["balance"] += account_rg["balance"]
                element[0]["amount_currency"] += account_rg["amount_currency"]
        if hide_account_at_0:
            tb_initial_acc = [p for p in tb_initial_acc if p["balance"] != 0]

        period_domain = self._get_period_ml_domain(
            account_ids,
            journal_ids,
            partner_ids,
            company_id,
            date_to,
            date_from,
            only_posted_moves,
            show_partner_details,
        )
        tb_period_acc = self.env["account.move.line"].read_group(
            domain=period_domain,
            fields=["account_id", "debit", "credit", "balance", "amount_currency"],
            groupby=["account_id"],
        )

        if show_partner_details:
            tb_initial_prt_bs = self.env["account.move.line"].read_group(
                domain=initial_domain_bs,
                fields=["account_id", "partner_id", "balance", "amount_currency"],
                groupby=["account_id", "partner_id"],
                lazy=False,
            )
            tb_initial_prt_pl = self.env["account.move.line"].read_group(
                domain=initial_domain_pl,
                fields=["account_id", "partner_id", "balance", "amount_currency"],
                groupby=["account_id", "partner_id"],
            )
            tb_initial_prt = tb_initial_prt_bs + tb_initial_prt_pl
            if hide_account_at_0:
                tb_initial_prt = [p for p in tb_initial_prt if p["balance"] != 0]
            tb_period_prt = self.env["account.move.line"].read_group(
                domain=period_domain,
                fields=[
                    "account_id",
                    "partner_id",
                    "debit",
                    "credit",
                    "balance",
                    "amount_currency",
                ],
                groupby=["account_id", "partner_id"],
                lazy=False,
            )
        total_amount = {}
        partners_data = []
        total_amount = self._compute_account_amount(
            total_amount, tb_initial_acc, tb_period_acc, foreign_currency
        )
        if show_partner_details:
            total_amount, partners_data = self._compute_partner_amount(
                total_amount, tb_initial_prt, tb_period_prt, foreign_currency
            )
        accounts_ids = list(total_amount.keys())
        unaffected_id = unaffected_earnings_account
        if unaffected_id not in accounts_ids:
            accounts_ids.append(unaffected_id)
            total_amount[unaffected_id] = {}
            total_amount[unaffected_id]["initial_balance"] = 0.0
            total_amount[unaffected_id]["balance"] = 0.0
            total_amount[unaffected_id]["credit"] = 0.0
            total_amount[unaffected_id]["debit"] = 0.0
            total_amount[unaffected_id]["ending_balance"] = 0.0
            if foreign_currency:
                total_amount[unaffected_id]["initial_currency_balance"] = 0.0
                total_amount[unaffected_id]["ending_currency_balance"] = 0.0
        accounts_data = self._get_accounts_data(accounts_ids)
        pl_initial_balance, pl_initial_currency_balance = self._get_pl_initial_balance(
            account_ids,
            journal_ids,
            partner_ids,
            company_id,
            fy_start_date,
            only_posted_moves,
            show_partner_details,
            foreign_currency,
        )
        total_amount[unaffected_id]["ending_balance"] += pl_initial_balance
        total_amount[unaffected_id]["initial_balance"] += pl_initial_balance
        if foreign_currency:
            total_amount[unaffected_id][
                "ending_currency_balance"
            ] += pl_initial_currency_balance
            total_amount[unaffected_id][
                "initial_currency_balance"
            ] += pl_initial_currency_balance
        return total_amount, accounts_data, partners_data


class ResCompany(models.Model):  # TEMP
    _inherit = "res.company"

    def compute_fiscalyear_dates(self, current_date):
        """Computes the start and end dates of the fiscal year where the given
        'date' belongs to.

        :param current_date: A datetime.date/datetime.datetime object.
        :return: A dictionary containing:
            * date_from
            * date_to
            * [Optionally] record: The fiscal year record.
        """
        self.ensure_one()
        date_str = current_date.strftime(DEFAULT_SERVER_DATE_FORMAT)

        # import pdb ; pdb.set_trace()
        # Search a fiscal year record containing the date.
        # If a record is found, then no need further computation, we get the
        # dates range directly.
        _LOGGER.info("BEFORE fiscalyear")
        fiscalyear = self.env["account.fiscal.year"].search(
            [
                ("company_id", "=", self.id),
                ("date_from", "<=", date_str),
                ("date_to", ">=", date_str),
            ],
            limit=1,
        )
        _LOGGER.info("AFTER fiscalyear")
        if fiscalyear:
            return {
                "date_from": fiscalyear.date_from,
                "date_to": fiscalyear.date_to,
                "record": fiscalyear,
            }

        date_from, date_to = date_utils.get_fiscal_year(
            current_date,
            day=self.fiscalyear_last_day,
            month=int(self.fiscalyear_last_month),
        )

        date_from_str = date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)
        date_to_str = date_to.strftime(DEFAULT_SERVER_DATE_FORMAT)

        # Search for fiscal year records reducing the delta between the date_from/date_to.
        # This case could happen if there is a gap between two fiscal year records.
        # E.g. two fiscal year records: 2017-01-01 -> 2017-02-01 and 2017-03-01 -> 2017-12-31.
        # => The period 2017-02-02 - 2017-02-30 is not covered by a fiscal year record.

        fiscalyear_from = self.env["account.fiscal.year"].search(
            [
                ("company_id", "=", self.id),
                ("date_from", "<=", date_from_str),
                ("date_to", ">=", date_from_str),
            ],
            limit=1,
        )
        if fiscalyear_from:
            date_from = fiscalyear_from.date_to + timedelta(days=1)

        fiscalyear_to = self.env["account.fiscal.year"].search(
            [
                ("company_id", "=", self.id),
                ("date_from", "<=", date_to_str),
                ("date_to", ">=", date_to_str),
            ],
            limit=1,
        )
        if fiscalyear_to:
            date_to = fiscalyear_to.date_from - timedelta(days=1)

        return {"date_from": date_from, "date_to": date_to}
