##############################################################################
#
# RM Approval Hierarchy
# Copyright (C) 2020 Opus Vision Limited (<https://opusvl.com>)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name": "RM Approval Hierarchy",
    "summary": "Manage approval hierarchy for RM",
    "category": "Tools",
    "author": "Opus Vision Limited",
    "website": "https://opusvl.com",
    "version": "13.0.0.0.2",
    # any module necessary for this one to work correctly
    "depends": [
        "approval_hierarchy",
        "royalmarsden",
        "uk_account_budget",
        "account_financial_report",
        "account_mtd_vat",
        "uk_account_asset",
        "sale",
        "purchase",
        "analytic",
    ],
    # always loaded
    "data": [
        "security/rm_custom_approval_security.xml",
        "security/ir.model.access.csv",
        "views/hr_job_views.xml",
        "views/account_move_menu_group_views.xml",
    ],
    "license": "AGPL-3",
}
