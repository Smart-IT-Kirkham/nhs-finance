from datetime import date

from odoo.tests.common import Form, SavepointCase

from ..helpers import redirect_setupclass_exception


class TestPurchaseCommon(SavepointCase):
    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(TestPurchaseCommon, cls).setUpClass()
        cls.po_obj = cls.env["purchase.order"]
        cls.pol_obj = cls.env["purchase.order.line"]
        cls.move_obj = cls.env["account.move"]
        cls.user_obj = cls.env["res.users"]
        # Set up the users which trigger / utilize purchase approval workflow
        cls.purchase_user = cls.env.ref(
            "base.user_demo"
        )  # Has Purchase --> User permission
        cls.purchase_manager_user = cls.create_user("purchasemanager@example.com")
        cls.supplier_a = cls.env.ref("base.res_partner_4")
        # Configure a seller against this demo product before we become a low
        # permission user, as to remove log spam saying access denied due to the
        # system adding it automatically at time of creating PO if it doesn't exist
        cls.purchasable_product_a = cls.env.ref("product.product_product_4d")
        # Needed to set qty on bill created on purchase
        cls.purchasable_product_a.purchase_method = "purchase"
        cls.env["product.supplierinfo"].create(
            dict(
                name=cls.supplier_a.id,
                sequence=1,
                min_qty=0.0,
                price=500.0,
                product_tmpl_id=cls.purchasable_product_a.product_tmpl_id.id,
                delay=0,
            )
        )

    @classmethod
    def create_user(cls, login):
        user = cls.user_obj.create(dict(name=login, login=login))
        user.partner_id.email = login
        return user


class PurchaseApprovalBase(TestPurchaseCommon):
    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(PurchaseApprovalBase, cls).setUpClass()
        cls.purchase_a = cls.po_obj.with_user(cls.purchase_user).create(
            dict(partner_id=cls.supplier_a.id)
        )
        # Make a line which sets the order above the default
        # minimum limit for purchase approval (5,000)
        cls.purchase_a_line_a = cls.pol_obj.with_user(cls.purchase_user).create(
            dict(
                order_id=cls.purchase_a.id,
                product_id=cls.purchasable_product_a.id,
                product_uom=cls.purchasable_product_a.uom_id.id,
                date_planned=date.today(),
                name="test",
                product_qty=500,
                price_unit=500,
            )
        )
        cls.purchase_a.with_user(cls.purchase_user).button_confirm()
        cls.expected_po_state = "to approve"

    def test_order_value_is_high_enough(self):
        self.assertTrue(
            self.purchase_a.amount_total >= 5000,
            "Expected purchase order amount to trigger default approval rule amount",
        )

    def test_po_in_correct_state(self):
        self.assertEqual(
            self.purchase_a.state,
            self.expected_po_state,
            "Expected purchase order to move into approval state",
        )


class TestPurchaseApprovalActions(PurchaseApprovalBase):
    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(TestPurchaseApprovalActions, cls).setUpClass()
        cls.purchase_a.with_user(cls.purchase_manager_user).button_approve()
        cls.expected_po_state = "purchase"

    def test_validation_date(self):
        self.assertEqual(
            self.purchase_a.validation_date,
            date.today(),
            "Expected validation date to be the date the PO was approved",
        )

    def test_validated_by_id(self):
        self.assertEqual(
            self.purchase_a.validated_by_id,
            self.purchase_manager_user.employee_id,
            "Expected Validated By to be the employee of the user who approved the PO",
        )


class TestCreateBillFromPurchaseActions(TestPurchaseApprovalActions):
    @classmethod
    @redirect_setupclass_exception
    def setUpClass(cls):
        super(TestCreateBillFromPurchaseActions, cls).setUpClass()
        invoice_action = cls.purchase_a.with_context(
            create_bill=True
        ).action_view_invoice()
        # Using Form plays correct onchanges and behaves same as in GUI
        vendor_bill = Form(
            cls.env["account.move"].with_context(invoice_action.get("context"))
        )
        cls.invoice = vendor_bill.save()

    def test_bill_linked_to_purchase(self):
        self.assertEqual(self.invoice.created_from_purchase_id, self.purchase_a)

    def test_bill_lines_created_correctly(self):
        # O2517, weirdness where creating a bill from a PO would result in
        # both quantity and price unit on all lines being set back to 0
        self.assertEqual(self.invoice.invoice_line_ids.price_unit, 500)
        # This one only works if product.purchase_method == 'purchase'
        self.assertEqual(self.invoice.invoice_line_ids.quantity, 500)
