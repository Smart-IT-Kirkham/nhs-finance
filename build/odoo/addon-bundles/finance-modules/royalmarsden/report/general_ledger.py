from odoo import models


class GeneralLedgerReport(models.AbstractModel):
    _inherit = "report.account_financial_report.general_ledger"

    # _get_initial_balance_data copied from
    # .../OCA_account-financial-reporting/account_financial_report/report/general_ledger.py
    # See git blame and the git history of this region to find out what we changed
    def _get_initial_balance_data(
        self,
        account_ids,
        partner_ids,
        company_id,
        date_from,
        foreign_currency,
        only_posted_moves,
        unaffected_earnings_account,
        fy_start_date,
        analytic_tag_ids,
        cost_center_ids,
        extra_domain,
    ):
        base_domain = []
        if company_id:
            base_domain += [("company_id", "=", company_id)]
        if partner_ids:
            base_domain += [("partner_id", "in", partner_ids)]
        if only_posted_moves:
            base_domain += [("move_id.state", "=", "posted")]
        else:
            base_domain += [("move_id.state", "in", ["posted", "draft"])]
        if analytic_tag_ids:
            base_domain += [("analytic_tag_ids", "in", analytic_tag_ids)]
        if cost_center_ids:
            base_domain += [("analytic_account_id", "in", cost_center_ids)]
        if extra_domain:
            base_domain += extra_domain
        initial_domain_bs = self._get_initial_balances_bs_ml_domain(
            account_ids, company_id, date_from, base_domain
        )
        initial_domain_pl = self._get_initial_balances_pl_ml_domain(
            account_ids, company_id, date_from, fy_start_date, base_domain
        )
        gl_initial_acc = self._get_accounts_initial_balance(
            initial_domain_bs, initial_domain_pl
        )
        initial_domain_acc_prt = self._get_initial_balances_bs_ml_domain(
            account_ids, company_id, date_from, base_domain, acc_prt=True
        )
        gl_initial_acc_prt = self.env["account.move.line"].read_group(
            domain=initial_domain_acc_prt,
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
        gen_ld_data = {}
        for gl in gl_initial_acc:
            acc_id = gl["account_id"][0]
            gen_ld_data[acc_id] = {}
            gen_ld_data[acc_id]["id"] = acc_id
            gen_ld_data[acc_id]["partners"] = False
            gen_ld_data[acc_id]["init_bal"] = {}
            gen_ld_data[acc_id]["init_bal"]["credit"] = gl["credit"]
            gen_ld_data[acc_id]["init_bal"]["debit"] = gl["debit"]
            gen_ld_data[acc_id]["init_bal"]["balance"] = gl["balance"]
            gen_ld_data[acc_id]["fin_bal"] = {}
            gen_ld_data[acc_id]["fin_bal"]["credit"] = gl["credit"]
            gen_ld_data[acc_id]["fin_bal"]["debit"] = gl["debit"]
            gen_ld_data[acc_id]["fin_bal"]["balance"] = gl["balance"]
            gen_ld_data[acc_id]["init_bal"]["bal_curr"] = gl["amount_currency"]
            gen_ld_data[acc_id]["fin_bal"]["bal_curr"] = gl["amount_currency"]
        partners_data = {}
        partners_ids = set()
        if gl_initial_acc_prt:
            for gl in gl_initial_acc_prt:
                if not gl["partner_id"]:
                    prt_id = 0
                    prt_name = "Missing Partner"
                else:
                    prt_id = gl["partner_id"][0]
                    prt_name = gl["partner_id"][1]
                    prt_name = prt_name._value
                if prt_id not in partners_ids:
                    partners_ids.add(prt_id)
                    partners_data.update({prt_id: {"id": prt_id, "name": prt_name}})
                acc_id = gl["account_id"][0]
                gen_ld_data[acc_id][prt_id] = {}
                gen_ld_data[acc_id][prt_id]["id"] = prt_id
                gen_ld_data[acc_id]["partners"] = True
                gen_ld_data[acc_id][prt_id]["init_bal"] = {}
                gen_ld_data[acc_id][prt_id]["init_bal"]["credit"] = gl["credit"]
                gen_ld_data[acc_id][prt_id]["init_bal"]["debit"] = gl["debit"]
                gen_ld_data[acc_id][prt_id]["init_bal"]["balance"] = gl["balance"]
                gen_ld_data[acc_id][prt_id]["fin_bal"] = {}
                gen_ld_data[acc_id][prt_id]["fin_bal"]["credit"] = gl["credit"]
                gen_ld_data[acc_id][prt_id]["fin_bal"]["debit"] = gl["debit"]
                gen_ld_data[acc_id][prt_id]["fin_bal"]["balance"] = gl["balance"]
                gen_ld_data[acc_id][prt_id]["init_bal"]["bal_curr"] = gl[
                    "amount_currency"
                ]
                gen_ld_data[acc_id][prt_id]["fin_bal"]["bal_curr"] = gl[
                    "amount_currency"
                ]
        accounts_ids = list(gen_ld_data.keys())
        unaffected_id = unaffected_earnings_account
        if unaffected_id not in accounts_ids:
            accounts_ids.append(unaffected_id)
            self._initialize_account(gen_ld_data, unaffected_id, foreign_currency)
        pl_initial_balance = self._get_pl_initial_balance(
            account_ids,
            company_id,
            fy_start_date,
            foreign_currency,
            base_domain,
        )
        gen_ld_data[unaffected_id]["init_bal"]["debit"] += pl_initial_balance["debit"]
        gen_ld_data[unaffected_id]["init_bal"]["credit"] += pl_initial_balance["credit"]
        gen_ld_data[unaffected_id]["init_bal"]["balance"] += pl_initial_balance[
            "balance"
        ]
        gen_ld_data[unaffected_id]["fin_bal"]["debit"] += pl_initial_balance["debit"]
        gen_ld_data[unaffected_id]["fin_bal"]["credit"] += pl_initial_balance["credit"]
        gen_ld_data[unaffected_id]["fin_bal"]["balance"] += pl_initial_balance[
            "balance"
        ]
        if foreign_currency:
            gen_ld_data[unaffected_id]["init_bal"]["bal_curr"] += pl_initial_balance[
                "bal_curr"
            ]
            gen_ld_data[unaffected_id]["fin_bal"]["bal_curr"] += pl_initial_balance[
                "bal_curr"
            ]
        return gen_ld_data, partners_data, partner_ids
