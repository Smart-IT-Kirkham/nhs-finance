{
    "name": "Royal Marsden",
    "version": "13.0.0.0.1",
    "author": "Opus Vision Limited",
    "website": "https://opusvl.com/",
    "summary": "Module for all Royal Marsden bespoke changes",
    "category": "",
    "images": ["static/description/MTD-Connector.png"],
    "depends": [
        "uk_accounting",
        "account",
        "account_bank_statement_import",
        "account_check_printing",
        "account_facturx",
        "account_financial_report",
        "account_mtd",
        "account_mtd_vat",
        "analytic",
        "auth_signup",
        "base_iban",
        "base_setup",
        "base_vat",
        "bus",
        "date_range",
        "digest",
        "fetchmail",
        "hr",
        "http_routing",
        "iap",
        "payment",
        "payment_transfer",
        "phone_validation",
        "portal",
        "product",
        "purchase",
        "report_xlsx",
        "resource",
        "sale",
        "UK_Reports",
        "form_width_increase",
    ],
    "data": [
        "data/account_payment_method.xml",
        "data/ir_sequence.xml",
        "data/res_config_settings.xml",
        "data/res_partner_bank_account_type.xml",
        "data/product.xml",
        "security/ir.model.access.csv",
        "views/webclient_template.xml",
        "views/account.xml",
        "views/purchase.xml",
        "views/res_bank.xml",
        "views/res_partner_bank.xml",
        "views/res_company.xml",
        "views/res_config_settings.xml",
        "views/res_partner.xml",
        "views/account_bank_statement_view.xml",
        "wizard/account_bankline_import.xml",
        "wizard/account_jac_import.xml",
    ],
    "demo": [
        "demo/account.xml",
        "demo/supplier.xml",
    ],
    "test": [],
    "application": True,
    "license": "AGPL-3",
    "installable": True,
    "auto_install": False,
}